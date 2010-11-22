import json, alfresco, sys, re, urllib2, getopt

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python purge-site.py siteurl|siteid [--username=username] [--password=username] [--url=username] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    _debug = 0
    sitename = ""
        
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
    
    if len(argv) > 0:
        siteurl = argv[0];
        idm = re.match('^(\w+)$', siteurl)
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
    
    sc = alfresco.ShareClient(url, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    print "Delete site '%s'" % (sitename)
    try:
        sc.deleteSite(sitename)
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
