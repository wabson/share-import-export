import json, alfresco, sys, getopt, os, mimetypes

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python export-users.py file.json [--username=username] [--password=username] [--url=username] [--skip-users=user1[,user2,...]] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    skip_users = [ 'System' ]
    downloadAvatars = True
    
    if len(argv) > 0:
        # File name to dump users to, or '-' for stdout
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "skip-users="])
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
        elif opt == "--skip-users":
            skip_users = arg.split(',')
    
    sc = alfresco.ShareClient(url, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get user information"
        pdata = sc.getAllUsers(getFullDetails=True, getDashboardConfig=True, getPreferences=True)
        
        # Remove unwanted users
        for p in pdata['people']:
            if p['userName'] in skip_users:
                pdata['people'].remove(p)
        
        if filename == '-':
            userJson = json.dumps(pdata, sort_keys=True, indent=4)
            print userJson
        else:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            
            # Download avatars
            if downloadAvatars:
                if not filename == "-":
                    print "Download profile images"
                for p in pdata['people']:
                    if 'avatar' in p:
                        # api/node/workspace/SpacesStore/259a1c59-d2db-4b3c-ba04-b4042de39821/content/thumbnails/avatar
                        # Download the original avatar, not the thumbnail
                        if not os.path.exists('%s/profile-images' % (os.path.dirname(filename))):
                            os.makedirs('%s/profile-images' % (os.path.dirname(filename)))
                        resp = sc.doGet('proxy/alfresco/%s' % (p['avatar'].replace('/thumbnails/avatar', '')))
                        # Detect image type from Content-Type header and guess extension (includes leading dot)
                        imgext = mimetypes.guess_extension(resp.info().gettype())
                        if imgext == ".jpe":
                            imgext = ".jpg"
                        imgfile = open('%s/profile-images/%s%s' % (os.path.dirname(filename), p['userName'], imgext), 'w')
                        imgfile.write(resp.read())
                        imgfile.close()
                        p['avatar'] = 'profile-images/%s%s' % (p['userName'], imgext)
                        
            # Write user data to a file
            userJson = json.dumps(pdata, sort_keys=True, indent=4)
            userfile = open(filename, 'w')
            userfile.write(userJson)
            userfile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
