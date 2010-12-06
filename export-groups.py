import json, alfresco, sys, getopt, os, mimetypes

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python export-groups.py file.json [--username=username] [--password=username] [--url=username] [--skip-groups=group1[,group2,...]] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    skip_groups = [ 'ALFRESCO_ADMINISTRATORS', 'EMAIL_CONTRIBUTORS' ]
    
    if len(argv) > 0:
        # File name to dump groups to, or '-' for stdout
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "skip-groups="])
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
        elif opt == "--skip-groups":
            skip_groups = arg.split(',')
    
    sc = alfresco.ShareClient(url, debug=_debug)
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
