import json, alfresco, sys, getopt, os

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python bootstrap-site.py file.json [--username=username] [--password=username] [--url=username] [--skip-missing-members] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    skip_missing_members = False
    create_site = True
    _debug = 0
    
    if len(argv) and not argv[0].startswith('-') > 0:
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "skip-missing-members", "no-create"])
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
        elif opt == '--skip-missing-members':
            skip_missing_members = True
        elif opt == '--no-create':
            create_site = False
    
    sc = alfresco.ShareClient(url=url, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        filenamenoext = os.path.splitext(os.path.split(filename)[1])[0]
        thisdir = os.path.dirname(filename)
        sd = json.loads(open(filename).read())
        siteId = str(sd['shortName'])
        if create_site:
            if sd['sitePreset'] == 'rm-site-dashboard':
                print "Create RM site '%s'" % (siteId)
                sc.createRmSite(sd)
            else:
                print "Create site '%s'" % (siteId)
                sc.createSite(sd)
        sc.setSitePages({'pages': sd['sitePages'], 'siteId': siteId})
        sc.updateSiteDashboardConfig(sd)
        # Add site members
        sc.addSiteMembers(siteId, sd['memberships'], skip_missing_members)
        # Import ACP files
        for container in [ 'documentLibrary', 'wiki', 'blog', 'calendar', 'discussions', 'links', 'dataLists', 'Saved Searches' ]:
            acpFile = thisdir + os.sep + '%s-%s.acp' % (filenamenoext, container.replace(' ', '_'))
            if os.path.isfile(acpFile):
                print "Import %s content" % (container)
                sc.importSiteContent(siteId, container, file(acpFile, 'rb'))
    except alfresco.SurfRequestError, e:
        if e.description == "error.duplicateShortName":
            print "Site with short name '%s' already exists" % (siteId)
            sys.exit(1)
        else:
            raise e
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
