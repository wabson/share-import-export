#! /usr/bin/env python
# export-groups.py

"""
Export group authorities from the repository in JSON format.

Usage: python export-groups.py file.json|- [options]

Options and arguments:

file.json         Name of the file to export groups to. Will be created if
                  it does not exist, or if it does the contents will be 
                  overwritten. Use - to specify stdout.

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

--tenant          Name of the tenant or Alfresco Cloud network to connect to

--skip-groups=arg Comma-separated list of group names to exclude from the 
                  export (do not prefix with 'GROUP_')

-d                Turn on debug mode

-h                Display this message
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
    skip_groups = [ 'ALFRESCO_ADMINISTRATORS', 'EMAIL_CONTRIBUTORS' ]
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-') and len(argv[0]) > 1:
            usage()
            sys.exit(1)
        else:
            # File name to dump groups to, or '-' for stdout
            filename = os.path.abspath(argv[0])
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "tenant=", "skip-groups="])
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
        elif opt == "--skip-groups":
            skip_groups = arg.split(',')
    
    sc = alfresco.ShareClient(url, tenant=tenant, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get group information"
        gdata = sc.getAllGroups(skip_groups)
        
        if filename == '-':
            groupJson = json.dumps(gdata, sort_keys=True, indent=4)
            print groupJson
        else:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            
            # Write user data to a file
            groupJson = json.dumps(gdata, sort_keys=True, indent=4)
            userfile = open(filename, 'w')
            userfile.write(groupJson)
            userfile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
