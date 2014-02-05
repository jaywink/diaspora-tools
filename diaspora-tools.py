#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  diaspora-tools.py
#  
#  Copyright 2013 Jason Robinson <jaywink@basshero.org>
#  
#  This source code is released under the MIT license 
#  (http://opensource.org/licenses/MIT).
#

from __future__ import print_function
import time
import argparse
import diaspy

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
    parser.add_argument('--wait', action='store_true', help="Wait for webfinger lookups to resolve")
    return parser.parse_args()

def connect(connstr):
    username = connstr.split(':')[0]
    password = connstr.split(':')[1].split('@')[0]
    host = connstr.split('@')[1]
    c = diaspy.connection.Connection(pod=host, username=username, password=password)
    c.login()
    return c
    
def connect_to_pods(args):
    print("INFO: connecting to",args.sourcepod.split('@')[1])
    sourcepod = connect(args.sourcepod)
    print("INFO: connecting to",args.targetpod.split('@')[1])
    targetpod = connect(args.targetpod)
    return sourcepod, targetpod

def close_connections(pods):
    print("INFO: Logging out of pods...")
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
    return conn.getUserData()['aspects']
    
def get_target_aspect(conn, source, args):
    while True:
        try:
            target = diaspy.models.Aspect(conn, name=source.name)
            break
        except OpenSSL.SSL.ZeroReturnError, e:
            print("DEBUG: error from diaspy.models.Aspect.__init__() - retrying, ctrl-c to stop...")
        except KeyboardInterrupt, e:
            return diaspy.models.Aspect(conn, id=-1, name=source.name)
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
    
def fetch_user(conn, user):
    person = diaspy.people.User(conn, handle=user['handle'], fetch='data')
    if person['id'] == 0:
        # try profile way, this could be a webfingered user not in contacts table
        person = diaspy.people.User(conn, guid=user['guid'], fetch='posts')
    return person

def migrate_contacts(args):
    pods = connect_to_pods(args)
    contacts = get_contacts(pods[0])
    aspects = pods[0].getUserData()['aspects']
    counts, processedguids = {'added':0, 'exists':0, 'notfound':0, 'unknownerrors':0, 'total':len(contacts), 'lookups':0}, []
    if not args.full:
        usercache = load_user_cache()
    if args.wait:
        attempts = 10
    else:
        attempts = 1
    for record in aspects:
        print("**** "+record['name']+" ****")
        source = diaspy.models.Aspect(pods[0], record['id'], record['name'])
        while True:
            try:
                users = source.getUsers()
                break
            except (AttributeError, OpenSSL.SSL.ZeroReturnError), e:
                print("DEBUG: error from diaspy.models.Aspect.getUsers() - retrying, ctrl-c to stop...")
            except KeyboardInterrupt, e:
                close_connections(pods)
                return counts
        print("Found",len(users),"users")
        target = get_target_aspect(pods[1], source, args)
        for user in contacts:
            if user['guid'] in users:
                print("Checking",user['handle'],user['guid'])
                for tries in range(attempts):
                    try:
                        person = fetch_user(pods[1], user)
                        if person['id'] == 0:
                            raise Exception()
                        elif not args.full and person['guid'] in usercache:
                            print("INFO: --in cache, skipping--")
                            break
                        try:
                            if not args.n:
                                add_to_aspect(pods[1], person['id'], target.id)
                                if not args.full and person['guid'] not in processedguids:
                                    processedguids.append(person['guid'])
                                print("INFO: ADDED",user['handle'],person['id'])
                            else:
                                print("INFO: [NO-OP mode] ADDED",user['handle'],person['id'])
                            counts['added'] += 1
                            break
                        except KeyboardInterrupt, e:
                            # User wants out
                            close_connections(pods)
                            return counts
                        except Exception, e:
                            print("ERROR:",e.message)
                            if e.message.find('400') > -1:
                                counts['exists'] += 1
                                if not args.full and person['guid'] not in processedguids:
                                    processedguids.append(person['guid'])
                                break
                            else:
                                counts['unknownerrors'] += 1
                                print("ERROR: unknown error")
                                break
                    except KeyboardInterrupt, e:
                        # User wants out
                        close_connections(pods)
                        return counts
                    except Exception, e:
                        if tries == 0:
                            counts['notfound'] += 1
                            print("INFO: Could not find user, triggering lookup")
                            # FIXME: Calling connection.get directly instead of using
                            # diaspy method which will appear in Search class but is not
                            # merged to master yet
                            #~ pods[1].lookup_user(user['handle'])
                            pods[1].get('people', headers={'accept': 'text/html'}, params={'q': user['handle']})
                            counts['lookups'] += 1
                        if args.wait and tries != attempts:
                            print("-- waiting --")
                            time.sleep(3)
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

