#! /usr/bin/env python
# export-site.py

"""
Export information on a specific collaboration or RM site in JSON format.

Usage: python export-site.py siteurl|siteid file.json|- [options]

Options and arguments:

siteurl|siteid    URL name of the site to export, alternatively the full site
                  dashboard URL can be used (also implies --url).

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

--export-content  Export content of each of the site components (in ACP format)
                  to disk, alongside the JSON file. Will be ignored if stdout
                  if specified for the output.
                  
--export-tags     Export tag information for each site component, in JSON 
                  format. ACP content exports do not support tag information
                  natively.

--no-metadata     Do not include basic site metadata in the site data

--no-memberships  Do not include site memberships in the site data

--no-pages        Do not include site pages in the site data

--no-dashboard    Do not include dashboard configuration in the site data

--containers=list Comma-separated list of container names to export site
                  content and tags for, e.g. documentLibrary,wiki

--async           Generate ACP files asyncronously, for use with --export-content

--include-paths=list Comma-separated list of folders or content items to include 
                  in the ACP file(s). This can be a list of absolute paths from 
                  the store root (although anything not inside the site will be 
                  ignored), or it can be relative to the site root. The path 
                  should be forward slash-separated and path parts are the child
                  assoc names, e.g. 'app:company_home'. If a prefix is not provided
                  then 'cm:' is assumed.
                  
                  You do not need to explicitly include every node you wish to 
                  export in the list, as all ancestor nodes and descendants of 
                  each list item will be automatically included. Note that other 
                  (non-child) associations are not followed.
                  
                  Note that specifying --include-paths=documentLibrary,wiki is
                  equivalent to --containers=documentLibrary,wiki.
                  
-d                Turn on debug mode

-h                Display this message
--help
"""

import getopt
import json
import os
import re
import sys
import time
import urllib

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
    sitename = ""
    filename = ""
    exportContent = False
    exportTags = False
    siteContainers = [ 'documentLibrary', 'wiki', 'blog', 'calendar', 'discussions', 'links', 'dataLists', 'Saved Searches' ]
    includePaths = None
    # Type of site metadata to get
    getMetaData = True
    getMemberships = True
    getPages = True
    getDashboardConfig = True
    async = False
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-') and len(argv[0]) > 1:
            usage()
            sys.exit(1)

    if len(argv) > 1:
    
        if not argv[1].startswith('-'):
            try:
                opts, args = getopt.getopt(argv[2:], "hdu:p:U:", 
                    ["help", "username=", "password=", "url=", "tenant=", "export-content", "async", "export-tags", "containers=", "include-paths=", "no-metadata", "no-memberships", "no-pages", "no-dashboard"])
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
                elif opt == '--export-content':
                    exportContent = True
                elif opt == '--async':
                    async = True
                elif opt == '--export-tags':
                    exportTags = True
                elif opt == '--containers':
                    siteContainers = arg.split(',')
                elif opt == '--include-paths':
                    includePaths = arg.split(',')
                elif opt == '--no-metadata':
                    getMetaData = False
                elif opt == '--no-memberships':
                    getMemberships = False
                elif opt == '--no-pages':
                    getPages = False
                elif opt == '--no-dashboard':
                    getDashboardConfig = False
            
            idm = re.match('^([\-\w]+)$', argv[0])
            urlm = re.match('^(https?\://[\w\-\.\:]+/share)/([\w\-\./_]+/)?page/site/([\-\w]+)/[\w\-\./_]*$', argv[0])
            if idm is not None:
                sitename = argv[0]
            elif urlm is not None:
                url = urlm.group(1)
                sitename = urlm.group(3)
                if urlm.group(2) is not None:
                    if tenant is None or tenant == urlm.group(2).strip('/'):
                        tenant = urlm.group(2).strip('/')
                    else:
                        raise Exception("Site URL '%s' is not compatible with given tenant ID '%s'" % (argv[0]), tenant)

            else:
                raise Exception("Not a valid site URL or ID (%s)" % (argv[0]))
            
            filename = argv[1]
        else:
            usage()
            sys.exit(1)
    else:
        usage()
        sys.exit(1)
    
    sc = alfresco.ShareClient(url, tenant=tenant, debug=_debug)
    if not filename == "-":
        print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    try:
        if not filename == "-":
            print "Get site information"
        sdata = sc.getSiteInfo(sitename, getMetaData, getMemberships, getPages, getDashboardConfig)
        
        if filename == '-':
            siteJson = json.dumps(sdata, sort_keys=True, indent=4)
            print siteJson
        else:
            if not os.path.exists(os.path.dirname(filename)) and os.path.dirname(filename) != '':
                os.makedirs(os.path.dirname(filename))
            
            # Download ACP files
            
            # Write site data to a file
            siteJson = json.dumps(sdata, sort_keys=True, indent=4)
            siteFile = open(filename, 'w')
            siteFile.write(siteJson)
            siteFile.close()
            
        if exportContent:
            if not filename == "-":
                print "Export all site content"
                tempContainerName = 'export-%s' % (int(time.time()))
                results = sc.exportAllSiteContent(sitename, siteContainers, includePaths, tempContainerName, async)
                
                if not async:
                    for component in results['exportFiles']:
                        acpFileName = "%s-%s.acp" % (os.path.splitext(filename)[0], component.replace(' ', '_'))
                        print "Saving %s" % (acpFileName)
                        resp = sc.doGet(urllib.quote('proxy/alfresco/api/path/content/workspace/SpacesStore/Company Home/%s/%s/%s/%s-%s.acp' % (sc.getSitesContainerName(), sitename, tempContainerName, sitename, component)))
                        acpfile = open(acpFileName, 'wb')
                        acpfile.write(resp.read())
                        acpfile.close()
                    
                    # Delete the 'export' folder afterwards
                    exportFolder = sc._getDocumentList('%s/%s/%s' % (sc.getSitesContainerName(), sitename, tempContainerName))
                    if exportFolder is not None:
                        sc.deleteFolder(exportFolder['metadata']['parent']['nodeRef'])
                else:
                    print '** ACP files will be generated asyncronously and will be available to download with a web browser using the following URLs **'
                    for component in results['exportFiles']:
                        print '%s/%s' % (sc.getRequestBase(), urllib.quote('proxy/alfresco/api/path/content/workspace/SpacesStore/Company Home/%s/%s/%s/%s-%s.acp' % (sc.getSitesContainerName(), sitename, tempContainerName, sitename, component)))

        if exportTags:
            if not filename == "-":
                print "Export site tag information"
                
                for container in siteContainers:
                    tagsData = sc.getSiteTagInfo(sitename, container)
                    if len(tagsData) > 0:
                        tagFileName = "%s-%s-tags.json" % (filename.replace('.json', ''), container.replace(' ', '_'))
                        print "Saving %s" % (tagFileName)
                        tagsJson = json.dumps({"items": tagsData}, indent=4)
                        tagsFile = open(tagFileName, 'w')
                        tagsFile.write(tagsJson)
                        tagsFile.close()
            
    finally:
        if not filename == "-":
            print "Log out (%s)" % (username)
        try:
            sc.doLogout()
        except Exception, e:
            pass

if __name__ == "__main__":
    main(sys.argv[1:])
