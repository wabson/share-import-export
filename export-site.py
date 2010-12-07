import getopt
import json
import os
import re
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python export-site.py siteurl|siteid file.json [--username=username] [--password=username] [--url=username] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    sitename = ""
    filename = ""
    
    try:
        opts, args = getopt.getopt(argv[2:], "hdu:p:U:", ["help", "username=", "password=", "url="])
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
    
    if len(argv) > 1:
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
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            
            # TODO Download ACP files
            
            # Write site data to a file
            siteJson = json.dumps(sdata, sort_keys=True, indent=4)
            siteFile = open(filename, 'w')
            siteFile.write(siteJson)
            siteFile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
