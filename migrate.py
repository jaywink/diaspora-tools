#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  migrate.py
#  
#  Copyright 2013 Jason Robinson <jaywink@basshero.org>
#  
#  This source code is released under the MIT license 
#  (http://opensource.org/licenses/MIT).
#

import argparse
import diaspy
from pprint import pprint

_description_ = """
    This program will help you to migrate your data from one
    Diaspora* pod to another.
    
    Currently only contact migration is supported and contacts
    must exist on pod where they are migrated to. Also all contacts
    will be added to 'imported' aspect.
"""

def arguments():
    parser = argparse.ArgumentParser(description=_description_)
    parser.add_argument('sourcepod', help='username:password@https://sourcepod.tld')
    parser.add_argument('targetpod', help='username:password@https://targetpod.tld')
    parser.add_argument('-n', action='store_true', help="Don't do any changes, just print out")
    return parser.parse_args()

def connect(connstr):
    username = connstr.split(':')[0]
    password = connstr.split(':')[1].split('@')[0]
    host = connstr.split('@')[1]
    c = diaspy.connection.Connection(pod=host, username=username, password=password)
    c.login()
    return c
    
def connect_to_pods(args):
    print("connecting to",args.sourcepod)
    sourcepod = connect(args.sourcepod)
    print("connecting to",args.targetpod)
    targetpod = connect(args.targetpod)
    return sourcepod, targetpod

def close_connections(pods):
    print("Logging out of pods...")
    for pod in pods:
        pod.logout()

def get_contacts(conn):
    contacts = diaspy.people.Contacts(conn)
    return contacts.get()
    
def get_aspects(conn):
    return conn.getUserInfo()['aspects']
    
def get_aspect_id(conn, name):
    aspects = diaspy.streams.Aspects(conn)
    aspect_id = aspects.getAspectID(name)
    if aspect_id == -1:
        aspect = aspects.add(name)
        aspect_id = aspect.id
    return aspect_id

def add_to_aspect(conn, user_id, aspect_id):
    aspect = diaspy.models.Aspect(conn, aspect_id)
    aspect.addUser(user_id)
    
def fetch_user(conn, handle):
    return diaspy.people.User(conn, handle=handle, fetch='data')

def migrate_contacts(args):
    pods = connect_to_pods(args)
    contacts = get_contacts(pods[0])
    aspect_id = get_aspect_id(pods[1], 'imported')
    
    counts = {'added':0, 'exists':0, 'notfound':0, 'unknownerrors':0, 'total':len(contacts)}
    
    for user in contacts:
        print("----")
        print("Adding",user['handle'],user['guid'])
        try:
            person = fetch_user(pods[1], user['handle'])
            if person['id'] == 0:
                raise Exception()
            try:
                if not args.n:
                    add_to_aspect(pods[1], person['id'], aspect_id)
                    print("ADDED",user['handle'],person['id'])
                    
                else:
                    print("[NO-OP mode] ADDED",user['handle'],person['id'])
                counts['added'] += 1
            except KeyboardInterrupt, e:
                # User wants out
                close_connections(pods)
                return counts
            except Exception, e:
                print(e.message)
                if e.message.find('400') > -1:
                    counts['exists'] += 1
                    print("ERROR - adding to aspect failed")
                elif e.message.find('404') > -1:
                    counts['notfound'] += 1
                    print("ERROR - could not find user (when adding)")
                else:
                    counts['unknownerrors'] += 1
                    print("ERROR - unknown error")
        except KeyboardInterrupt, e:
            # User wants out
            close_connections(pods)
            return counts
        except Exception, e:
            print("ERROR - could not find user")
            counts['notfound'] += 1
    close_connections(pods)
    return counts

def main():
    args = arguments()
    
    counts = migrate_contacts(args)
    print(counts)
    
    return 0

if __name__ == '__main__':
    main()

