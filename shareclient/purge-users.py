#! /usr/bin/env python
# purge-users.py

"""
Delete users defined in a local JSON file from the repository.

Usage: python purge-users.py file.json [options]

Options and arguments:

file.json         Name of the JSON file to load user details from

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

--tenant          Name of the tenant or Alfresco Cloud network to connect to

--users=arg       Comma-separated list of user names to remove. Users in the
                  JSON file whose user names do not exactly match one of the 
                  values will be skipped and not deleted.

--skip-users=arg  Comma-separated list of user names to exclude from the 
                  deletion

-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
import json
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print __doc__

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    tenant = None
    include_users = None
    skip_users = [ 'System', 'admin', 'guest' ]
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            # File name to load users from
            filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "tenant=", "users=", "skip-users="])
    except getopt.GetoptError, e:
        print e
        usage()
        sys.exit(1)
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == '-d':
            _debug = 1
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-U", "--url"):
            url = arg
        elif opt == "--tenant":
            tenant = arg
        elif opt == "--users":
            include_users = arg.split(',')
        elif opt == "--skip-users":
            skip_users = arg.split(',')
    
    sc = alfresco.ShareClient(url, tenant=tenant, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        users = json.loads(open(filename).read())['people']
        purge_users = []
        
        # Filter the users
        for u in users:
            if (include_users is None or str(u['userName']) in include_users) and u['userName'] not in skip_users:
                purge_users.append(u)
        
        # Remove the users
        print "Delete %s user(s)" % (len(purge_users))
        sc.deleteUsers(purge_users)
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
