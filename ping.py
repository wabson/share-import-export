import getopt
import os
import re
import socket
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python ping.py [--username=username] [--password=username] [--url=username] [--timeout=timeout] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    # timeout in seconds
    timeout = 10
    
    try:
        opts, args = getopt.getopt(argv, "hdu:p:U:", ["help", "username=", "password=", "url="])
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
        elif opt == '--timeout':
            timeout = arg
    
    socket.setdefaulttimeout(timeout)
    
    sc = alfresco.ShareClient(url, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    print "Log out (%s)" % (username)
    sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
