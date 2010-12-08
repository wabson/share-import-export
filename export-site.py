#! /usr/bin/env python
# export-site.py

"""
Export information on a specific collaboration or RM site in JSON format.

Usage: python export-site.py siteurl|siteid file.json|- [options]

Options and arguments:

siteurl|siteid    URL name of the site to export, alternatively the full site
                  dashboard URL can be used (also implies --url).

file.json         Name of the file to export information to. Will be created if
                  it does not exist, or if it does the contents will be 
                  overwritten. Use - to specify stdout.

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
import json
import os
import re
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
    _debug = 0
    sitename = ""
    filename = ""
    exportContent = False
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-') and len(argv[0]) > 1:
            usage()
            sys.exit(1)

    if len(argv) > 1:
    
        if not argv[1].startswith('-'):
            try:
                opts, args = getopt.getopt(argv[2:], "hdu:p:U:", ["help", "username=", "password=", "url=", "export-content"])
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
                elif opt == '--export-content':
                    exportContent = True
            
            idm = re.match('^(\w+)$', argv[0])
            urlm = re.match('^(https?\\://[\w\\-\\.\\:]+/share)/page/site/(\w+)/[\w\\-\\./]*$', argv[0])
            if idm is not None:
                sitename = argv[0]
            elif urlm is not None:
                url = urlm.group(1)
                sitename = urlm.group(2)
            else:
                raise Exception("Not a valid site URL or ID (%s)" % (argv[0]))
            
            filename = argv[1]
        else:
            usage()
            sys.exit(1)
    else:
        usage()
        sys.exit(1)
    
    sc = alfresco.ShareClient(url, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get site information"
        sdata = sc.getSiteInfo(sitename, True, True, True, True)
        
        if filename == '-':
            siteJson = json.dumps(sdata, sort_keys=True, indent=4)
            print siteJson
        else:
            if not os.path.exists(os.path.dirname(filename)) and os.path.dirname(filename) != '':
                os.makedirs(os.path.dirname(filename))
            
            # TODO Download ACP files
            
            # Write site data to a file
            siteJson = json.dumps(sdata, sort_keys=True, indent=4)
            siteFile = open(filename, 'w')
            siteFile.write(siteJson)
            siteFile.close()
            
        if exportContent:
            if not filename == "-":
                print "Export all site content"
            sc.exportAllSiteContent(sitename)
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
