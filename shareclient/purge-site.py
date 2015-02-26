#! /usr/bin/env python
# purge-site.py

"""
Delete a site and all associated site data from the repository.

Usage: python purge-site.py siteurl|siteid [options]

Options and arguments:

siteurl|siteid    URL name of the site to remove, alternatively the full site
                  dashboard URL can be used (also implies --url).

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

--tenant          Name of the tenant or Alfresco Cloud network to connect to

-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
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
    tenant = None
    _debug = 0
    sitename = ""
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
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
    
    if len(argv) > 0:
        siteurl = argv[0];
        idm = re.match('^[ ]*[0-9a-zA-Z\-]+[ ]*$', siteurl)
        urlm = re.match('^(https?\\://[\w\\-\\.\\:]+/share)/page/site/(\w+)/[\w\\-\\./]*$', siteurl)
        if idm is not None:
            
            sitename = idm.group(0)
        elif urlm is not None:
            url = urlm.group(1)
            sitename = urlm.group(2)
        else:
            raise Exception("Not a valid site URL or ID (%s)" % (siteurl))
    else:
        usage()
        sys.exit(1)
    
    sc = alfresco.ShareClient(url, tenant=tenant, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    print "Delete site '%s'" % (sitename)
    try:
        sc.deleteSite(sitename)
        """site shortname is blocked by site in trashcan - https://issues.alfresco.com/jira/browse/ACE-2756"""
        print "... Deleted site '%s' - site shortname is locked by site in user trashcan (delete in profile)" % (sitename)
    except alfresco.SurfRequestError, e:
        if e.code == 404:
            print "Site '%s' does not exist" % (sitename)
        else:
            raise e
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
