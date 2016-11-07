#! /usr/bin/env python
# import-groups.py

"""
Import nested category definitions from the local file system.

Usage: python import-categories.py file.json [options]

Options and arguments:

file.json              Name of the JSON file to import information from.

-u user                The username to authenticate as
--username=user

-p pass                The password to authenticate with
--password=pass

-U url                 The URL of the Share web application, e.g. 
--url=url              http://alfresco.test.com/share

--tenant               Name of the tenant or Alfresco Cloud network to connect to

-d                     Turn on debug mode

-h                     Display this message
--help
"""

import getopt
import json
import os
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
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            filename = argv[0]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "tenant="])
    except getopt.GetoptError, e:
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
    
    sc = alfresco.ShareClient(url=url, tenant=tenant, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        filenamenoext = os.path.splitext(os.path.split(filename)[1])[0]
        thisdir = os.path.dirname(filename)
        gd = json.loads(open(filename).read())
        for category in gd['categories']:
            sc.createCategories(category)
        
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
