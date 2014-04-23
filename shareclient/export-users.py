#! /usr/bin/env python
# export-users.py

"""
Export user definitions from the repository in JSON format. This will export 
ALL repository users (subject to the --skip-users option), including any which 
have been imported from LDAP.

Usage: python export-users.py file.json|- [options]

Options and arguments:

file.json         Name of the file to export information to. Will be created if
                  it does not exist, or if it does the contents will be 
                  overwritten. Use - to specify stdout.

-u user           The username to authenticate as
--username=user

-p pass           The password to authenticate with
--password=pass

-U url            The URL of the Share web application, e.g. 
--url=url         http://alfresco.test.com/share

--tenant          Name of the tenant or Alfresco Cloud network to connect to

--users=arg       Comma-separated list of user names to export. Users in the
                  whose user names do not exactly match one of the values will 
                  be skipped and not exported.

--skip-users=arg  Comma-separated list of usernames to exclude from the 
                  export

--no-avatars      Do not download user profile images

--avatar-thumbnail Name of the thumbnail to download (default is original 
                  profile image that was uploaded)

-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
import json
import mimetypes
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
    include_users = None
    skip_users = [ 'System' ]
    downloadAvatars = True
    avatarThumbnail = None
    isCloud = False
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-') and len(argv[0]) > 1:
            usage()
            sys.exit(1)
        else:
            # File name to dump users to, or '-' for stdout
            filename = os.path.abspath(argv[0])
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "tenant=", "users=", "skip-users=", "no-avatars", "avatar-thumbnail=", "cloud"])
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
        elif opt == "--no-avatars":
            downloadAvatars = False
        elif opt == "--avatar-thumbnail":
            avatarThumbnail = arg
        elif opt == "--users":
            include_users = arg.split(',')
        elif opt == "--skip-users":
            skip_users = arg.split(',')
        elif opt == "--cloud":
            isCloud = True
    
    sc = alfresco.ShareClient(url, tenant=tenant, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get user information"
        if not isCloud:
            pdata = sc.getAllUsers(getFullDetails=True, getDashboardConfig=True, getPreferences=False, getGroups=True)
        else:
            pdata = sc.getCloudUsers(getFullDetails=True, getDashboardConfig=False, getPreferences=False, getGroups=True)
        export_users = []
        
        # Filter the users
        for u in pdata['people']:
            if (include_users is None or str(u['userName']) in include_users) and u['userName'] not in skip_users:
                export_users.append(u)
        
        # Export a dict object
        export = { 'people': export_users }
        
        if filename == '-':
            userJson = json.dumps(export, sort_keys=True, indent=4)
            print userJson
        else:
            thisdir = os.path.dirname(filename)
            if thisdir == "":
                thisdir = os.getcwd()
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            
            # Download avatars
            if downloadAvatars and filename != "-":
                print "Download profile images"
                for p in export['people']:
                    if 'avatar' in p:
                        if not os.path.exists('%s/profile-images' % (thisdir)):
                            os.makedirs('%s/profile-images' % (thisdir))
                        # Thumbnail will be something like
                        # /api/node/workspace/SpacesStore/259a1c59-d2db-4b3c-ba04-b4042de39821/content/thumbnails/avatar
                        # We want to download the original avatar, not the thumbnail
                        avatarUrl = (p['avatar'].replace('/thumbnails/avatar', ''))
                        if avatarThumbnail is not None:
                            avatarUrl = "%s/thumbnails/%s" % (avatarUrl, avatarThumbnail)
                        resp = sc.doGet('proxy/alfresco/%s' % (avatarUrl))
                        # Detect image type from Content-Type header and guess extension (includes leading dot)
                        imgext = mimetypes.guess_extension(resp.info().gettype())
                        if imgext == ".jpe":
                            imgext = ".jpg"
                        imgfile = open('%s/profile-images/%s%s' % (thisdir, p['userName'], imgext), 'wb')
                        imgfile.write(resp.read())
                        resp.close()
                        imgfile.close()
                        p['avatar'] = 'profile-images/%s%s' % (p['userName'], imgext)
                        
            # Write user data to a file
            userJson = json.dumps(export, sort_keys=True, indent=4)
            userfile = open(filename, 'w')
            userfile.write(userJson)
            userfile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
