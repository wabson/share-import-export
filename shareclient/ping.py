#! /usr/bin/env python
# ping.py

"""
Perform a basic login test against the repository. The script sets the socket
timeout to ten minutes (unless overridden by --timeout) and blocks until either
this time or until a log in and log out operation has been completed.

This can be used to 'pause' execution of a program until, for instance, the
Alfresco/Share server has fully started up.

Usage: python ping.py [options]

Options and arguments:

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

--tenant          Name of the tenant or Alfresco Cloud network to connect to

--timeout         Timeout value to set in seconds

-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
import os
import re
import socket
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
    # timeout in seconds
    timeout = 10
    
    try:
        opts, args = getopt.getopt(argv, "hdu:p:U:", ["help", "username=", "password=", "url=", "tenant="])
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
        elif opt == '--tenant':
            tenant = arg
        elif opt == '--timeout':
            timeout = arg
    
    socket.setdefaulttimeout(timeout)
    
    sc = alfresco.ShareClient(url, debug=_debug, tenant=tenant)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    print "Log out (%s)" % (username)
    sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
