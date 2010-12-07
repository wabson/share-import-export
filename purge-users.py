import getopt
import json
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python purge-users.py file.json [--username=username] [--password=username] [--url=username] [--skip-users=user1[,user2,...]] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    skip_users = [ 'System', 'admin', 'guest' ]
    _debug = 0
    
    if len(argv) > 0:
        # File name to dump users to, or '-' for stdout
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "skip-users="])
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
    
    sc = alfresco.ShareClient(url, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        users = json.loads(open(filename).read())['people']
        for u in users:
            if u['userName'] in skip_users:
                users.remove(u)
        print "Delete %s user(s)" % (len(users))
        sc.deleteUsers(users)
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
