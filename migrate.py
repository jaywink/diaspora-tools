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
    must exist on pod where they are migrated to. Any aspects missing
    from target pod will be created there.
    
    A "done" user cache file .diaspora-tools-migrate-user-cache will be
    created in working directory where script is executed. If this
    file exists, user guids there will not be added to any aspects.
    User cache file can be ignored by passing in --full as a parameter.
"""

def arguments():
    parser = argparse.ArgumentParser(description=_description_)
    parser.add_argument('sourcepod', help='username:password@https://sourcepod.tld')
    parser.add_argument('targetpod', help='username:password@https://targetpod.tld')
    parser.add_argument('-n', action='store_true', help="Don't do any changes, just print out")
    parser.add_argument('--full', action='store_true', help="Sync all users in all aspects, ignore user cache file")
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
        
def save_user_cache(users):
    cachef = open('.diaspora-tools-migrate-user-cache', 'a')
    for user in users:
        cachef.write(user+'\n')
    cachef.close()
    
def load_user_cache():
    users = []
    try:
        cachef = open('.diaspora-tools-migrate-user-cache', 'r')
        for line in cachef:
            users.append(line.strip('\r\n'))
        cachef.close()
    except:
        pass
    return users

def get_contacts(conn):
    contacts = diaspy.people.Contacts(conn)
    return contacts.get()
    
def get_aspects(conn):
    return conn.getUserInfo()['aspects']
    
def get_target_aspect(conn, source, args):
    target = diaspy.models.Aspect(conn, name=source.name)
    if not target.id:
        if not args.n:
            # create aspect
            aspects = diaspy.streams.Aspects(conn)
            target = aspects.add(source.name)
        else:
            return diaspy.models.Aspect(conn, id=-1, name=source.name)
    return target

def add_to_aspect(conn, user_id, aspect_id):
    aspect = diaspy.models.Aspect(conn, aspect_id)
    aspect.addUser(user_id)
    
def fetch_user(conn, handle):
    return diaspy.people.User(conn, handle=handle, fetch='data')

def migrate_contacts(args):
    pods = connect_to_pods(args)
    contacts = get_contacts(pods[0])
    aspects = pods[0].getUserInfo()['aspects']
    counts, processedguids = {'added':0, 'exists':0, 'notfound':0, 'unknownerrors':0, 'total':len(contacts)}, []
    if not args.full:
        usercache = load_user_cache()
    for record in aspects:
        print("**** "+record['name']+" ****")
        source = diaspy.models.Aspect(pods[0], record['id'], record['name'])
        users = source.getUsers()
        print("Found ",len(users),"users")
        target = get_target_aspect(pods[1], source, args)
        for user in contacts:
            if user['guid'] in users:
                print("Checking",user['handle'],user['guid'])
                try:
                    person = fetch_user(pods[1], user['handle'])
                    if person['id'] == 0:
                        raise Exception()
                    elif not args.full and person['guid'] in usercache:
                        print("--in cache, skipping--")
                        continue
                    try:
                        if not args.n:
                            add_to_aspect(pods[1], person['id'], target.id)
                            if not args.full and person['guid'] not in processedguids:
                                processedguids.append(person['guid'])
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
                            if not args.full and person['guid'] not in processedguids:
                                processedguids.append(person['guid'])
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
                print("----")
    close_connections(pods)
    if not args.full:
        save_user_cache(processedguids)
    return counts

def main():
    args = arguments()
    
    counts = migrate_contacts(args)
    print(counts)
    
    return 0

if __name__ == '__main__':
    main()

