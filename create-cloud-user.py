#! /usr/bin/env python
# import-site.py

"""
Create an Alfresco cloud user account - for development purposes only!

Usage: python import-cloud-user.py email [options]

Options and arguments:

email                       E-mail address to supply for the system sign-up page

-u user                     The username to authenticate as when creating the account (must be a superuser)
--username=user

-p pass                     The password to authenticate with when creating the user
--password=pass

-U url                      The URL of the Share web application, e.g. 
--url=url                   http://alfresco.test.com/share

--firstname                 First name of the new user

--lastname                  Last name of the new user

--userpassword              Password of the new user (optional, will prompt if not specified)
"""

import getopt
import getpass
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
    email = None
    firstname = None
    lastname = None
    userpassword = None
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            email = argv[0]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "debug", "firstname=", "lastname=", "userpassword="])
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
        elif opt in ("-p", "--firstname"):
            firstname = arg
        elif opt in ("-p", "--lastname"):
            lastname = arg
        elif opt in ("-p", "--userpassword"):
            userpassword = arg
        elif opt in ("-U", "--url"):
            url = arg
        elif opt in ("-d", "--debug"):
            _debug = 1

    # Check mandatory parameters
    if firstname is None:
        print "You must supply a first name for the new user"
        sys.exit(1)
    if firstname is None:
        print "You must supply a last name for the new user"
        sys.exit(1)
    if userpassword is None:
        pass1 = "1"
        pass2 = "2"
        while pass1 != pass2:
            pass1 = getpass.getpass("Enter user password: ")
            pass2 = getpass.getpass("Re-type user password: ")
        userpassword = pass1
    
    sc = alfresco.ShareClient(url=url, tenant="-system-", debug=_debug)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        qd = sc.doJSONPost("proxy/alfresco/internal/cloud/accounts/signupqueue", {'email': email, 'source': 'test-share-signup-page'})
    finally:
        sc.doLogout()
    usc = alfresco.ShareClient(url=url, tenant='-default-', debug=_debug)
    try:
        ud = usc.doJSONPost('proxy/alfresco-noauth/internal/cloud/account-activations', {'key': str(qd['registration']['key']), 'id': str(qd['registration']['id']), 'firstName': firstname, 'lastName': lastname, 'password': userpassword})
        """
Response will look like this

{
   "data":
   {
      "registration" :    {
      "email": "test1@alfresco.com",
      "registrationDate": "2012-07-09T22:55:37.000+01:00",
      "id": "activiti$401",
      "key": "200b2b10-c0ff-439d-9f99-cefa969e3ecd"
   }
, 
  "default": 1,
  "home": {    "id": 1,
   "name": "alfresco.com",
   "type": 0,
   "enabled" : true,
   "className": "PRIVATE_EMAIL_DOMAIN",
   "classDisplayName": "Free",
   "creationDate": "2012-07-03T19:06:08.000+01:00",
   "usageQuota":
   {
      "fileUploadSizeUQ": { "q" : 52428800 },
      "fileSizeUQ": { "u" : 5544313, "q" : 5368709120 },
      "siteCountUQ": { "u" : 2, "q" : -1 },
      "personCountUQ": { "u" : 2, "q": -1 },
      "personIntOnlyCountUQ": { "u" : 2, "q" : -1 },
      "personNetworkAdminCountUQ": { "u" : 0, "q" : 0 }
   },
   "domains":
   [
      "alfresco.com"
   ],
   "tenant": "alfresco.com"
 },
  "secondary": [
  ]
   }
}
        """
        sc.doLogout()
    finally:
        pass

if __name__ == "__main__":
    main(sys.argv[1:])
