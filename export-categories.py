import getopt
import json
import os
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python export-categories.py file.json [--username=username] [--password=username] [--url=username] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    
    if len(argv) > 0:
        # File name to dump categories to, or '-' for stdout
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url="])
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
    
    sc = alfresco.ShareClient(url, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get category information"
        cdata = { 'categories': sc.getAllCategories(), 'tags': sc.getAllTags() }
        
        if filename == '-':
            categoryJson = json.dumps(cdata, sort_keys=True, indent=4)
            print categoryJson
        else:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            
            # Write user data to a file
            categoryJson = json.dumps(cdata, sort_keys=True, indent=4)
            userfile = open(filename, 'w')
            userfile.write(categoryJson)
            userfile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
