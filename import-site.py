import getopt
import json
import os
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print "Usage: python import-site.py file.json [--username=username] [--password=username] [--url=username] [--skip-missing-members] [--containers=container1,...] [--no-content] [-d]"

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    skip_missing_members = False
    create_site = True
    add_members = True
    update_config = True
    update_dashboard = True
    siteContainers = [ 'documentLibrary', 'wiki', 'blog', 'calendar', 'discussions', 'links', 'dataLists', 'Saved Searches' ]
    _debug = 0
    
    if len(argv) and not argv[0].startswith('-') > 0:
        filename = argv[0]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "skip-missing-members", "no-members", "no-create", "no-configuration", "no-dashboard", "containers=", "no-content"])
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
        elif opt == '--containers':
            siteContainers = arg.split(',')
        elif opt == '--no-content':
            siteContainers = []
        elif opt == '--no-configuration':
            update_config = False
        elif opt == '--no-members':
            add_members = False
        elif opt == '--no-dashboard':
            update_dashboard = False
    
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
        if update_config:
            print "Set site configuration"
            sc.setSitePages({'pages': sd['sitePages'], 'siteId': siteId})
        if update_dashboard:
            print "Set dashboard configuration"
            sc.updateSiteDashboardConfig(sd)
        # Add site members
        if add_members:
            print "Add site members"
            sc.addSiteMembers(siteId, sd['memberships'], skip_missing_members)
        # Import ACP files
        for container in siteContainers:
            acpFile = thisdir + os.sep + '%s-%s.acp' % (filenamenoext, container.replace(' ', '_'))
            if os.path.isfile(acpFile):
                print "Import %s content" % (container)
                if siteId == 'rm' and container == 'documentLibrary':
                    sc.importRmSiteContent(siteId, container, file(acpFile, 'rb'))
                else:
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
