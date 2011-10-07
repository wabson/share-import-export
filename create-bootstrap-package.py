#! /usr/bin/env python
# create-bootstrap-package.py

"""
Import a site definition and site content from the local file system.

Usage: python create-bootstrap-package.py site-file.json package-file.jar [options]

Options and arguments:

site-file.json              Name of the JSON file to read site data from

package-file.jar            Name of the JAR file to package information inside

--create-missing-members    Auto-create any members who do not exist in the 
                            repository

--groups-file               Local file name to read group information from in JSON
                            format. Group information will be repackaged into text
                            format before being placed inside the JAR.

--users-file                Local file name to read user information from in JSON
                            format. User information will be repackaged into ACP
                            format before being placed inside the JAR.

--site-file                 Local file name to read site information from in JSON
                            format. Site information and content will be repackaged 
                            into a single ACP file.

--containers=list           Comma-separated list of container names to import site
                            content into, e.g. documentLibrary,wiki

-d                          Turn on debug mode

-h                          Display this message
--help
"""

import getopt
import json
import os
import sys
import xml.etree.ElementTree as etree
import zipfile
import locale
import re
import tempfile
import shutil
import mimetypes
import hashlib

import alfresco

global NSMAP
NSMAP = {
     'nt': 'http://www.jcp.org/jcr/nt/1.0',
     'rn': 'http://www.alfresco.org/model/rendition/1.0',
     'sys': 'http://www.alfresco.org/model/system/1.0',
     'lnk': 'http://www.alfresco.org/model/linksmodel/1.0',
     'gd': 'http://www.alfresco.org/model/googledocs/1.0',
     'ver': 'http://www.alfresco.org/model/versionstore/1.0',
     'cmiscustom': 'http://www.alfresco.org/model/cmis/custom',
     'jcr': 'http://www.jcp.org/jcr/1.0',
     'emailserver': 'http://www.alfresco.org/model/emailserver/1.0',
     'fm': 'http://www.alfresco.org/model/forum/1.0',
     'ia': 'http://www.alfresco.org/model/calendar',
     'rule': 'http://www.alfresco.org/model/rule/1.0',
     'wcm': 'http://www.alfresco.org/model/wcmmodel/1.0',
     'sv': 'http://www.jcp.org/jcr/sv/1.0',
     'dl': 'http://www.alfresco.org/model/datalist/1.0',
     'st': 'http://www.alfresco.org/model/site/1.0',
     'usr': 'http://www.alfresco.org/model/user/1.0',
     'exif': 'http://www.alfresco.org/model/exif/1.0',
     'app': 'http://www.alfresco.org/model/application/1.0',
     'module': 'http://www.alfresco.org/system/modules/1.0',
     'd': 'http://www.alfresco.org/model/dictionary/1.0',
     'blg': 'http://www.alfresco.org/model/blogintegration/1.0',
     'alf': 'http://www.alfresco.org',
     'cmis': 'http://www.alfresco.org/model/cmis/1.0/cs01',
     'mix': 'http://www.jcp.org/jcr/mix/1.0',
     'wca': 'http://www.alfresco.org/model/wcmappmodel/1.0',
     'bpm': 'http://www.alfresco.org/model/bpm/1.0',
     'inwf': 'http://www.alfresco.org/model/workflow/invite/nominated/1.0',
     'imap': 'http://www.alfresco.org/model/imap/1.0',
     'cm': 'http://www.alfresco.org/model/content/1.0',
     'reg': 'http://www.alfresco.org/system/registry/1.0',
     'ver2': 'http://www.alfresco.org/model/versionstore/2.0',
     'stcp': 'http://www.alfresco.org/model/sitecustomproperty/1.0',
     'wcmwf': 'http://www.alfresco.org/model/wcmworkflow/1.0',
     'view': 'http://www.alfresco.org/view/repository/1.0',
     'imwf': 'http://www.alfresco.org/model/workflow/invite/moderated/1.0',
     'act': 'http://www.alfresco.org/model/action/1.0',
     'wf': 'http://www.alfresco.org/model/workflow/1.0',
     'trx': 'http://www.alfresco.org/model/transfer/1.0',
     'rma': 'http://www.alfresco.org/model/recordsmanagement/1.0',
     'dod': 'http://www.alfresco.org/model/dod5015/1.0',
     'rmc': 'http://www.alfresco.org/model/rmcustom/1.0',
     'trx': 'http://www.alfresco.org/model/transfer/1.0'
}

global URI_CONTENT_1_0, URI_SYSTEM_1_0, URI_USER_1_0, URI_SITE_1_0, URI_REPOSITORY_1_0
URI_CONTENT_1_0 = 'http://www.alfresco.org/model/content/1.0'
URI_SYSTEM_1_0 = 'http://www.alfresco.org/model/system/1.0'
URI_USER_1_0 = 'http://www.alfresco.org/model/user/1.0'
URI_SITE_1_0 = 'http://www.alfresco.org/model/site/1.0'
URI_REPOSITORY_1_0 = 'http://www.alfresco.org/view/repository/1.0'

global DEFAULT_LOCALE
DEFAULT_LOCALE = locale.getdefaultlocale(locale.LC_ALL)[0]

# HTTP debugging flag
global _debug

def usage():
    print __doc__

def main(argv):

    site_file = None
    jar_file = None
    users_file = ''
    groups_file = ''
    users = None
    siteContainers = [ 'documentLibrary', 'wiki', 'blog', 'calendar', 'discussions', 'links', 'dataLists', 'Saved Searches' ]
    includeContent = True
    _debug = 0
    
    if len(argv) > 1:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            site_file = argv[0]
            jar_file = argv[1]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[2:], "hdu:p:U:", ["help", "users-file=", "groups-file=", "site-file=", "containers=", "no-content"])
    except getopt.GetoptError, e:
        usage()
        sys.exit(1)
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == '-d':
            _debug = 1
        elif opt == '--users-file':
            users_file = arg
        elif opt == '--groups-file':
            groups_file = arg
        elif opt == '--containers':
            siteContainers = arg.split(',')
        elif opt == '--no-content':
            includeContent = False
    
    if site_file is None:
        print "No site file specified"
        sys.exit(1)
    
    filenamenoext = os.path.splitext(os.path.split(site_file)[1])[0]
    thisdir = os.path.dirname(site_file)
    if thisdir == "":
        thisdir = "."
    sd = json.loads(open(site_file).read())
    
    # Temp working locations
    temppath = tempfile.mkdtemp(prefix='site-bootstrap-tmp-')
    
    baseName = os.path.splitext(os.path.basename(jar_file))[0]
    
    # Generate the site ACP file - should generate ACP file in temppath
    generateContentACP('%s-content.acp' % (baseName), sd, site_file, temppath, includeContent, siteContainers)
    
    # People files
    if users_file != '':
        generatePeopleACP('%s-people.acp' % (baseName), sd, users_file, temppath, users)
        generateUsersACP('%s-users.acp' % (baseName), sd, users_file, temppath, users)
        generateGroupsData('%s-groups.txt' % (baseName), sd, users_file, temppath, users)
    else:
        print 'WARNING: No user data supplied. Use --users-file=blah.json to include user info'
    
    # Build JAR file in current directory
    jarFile = zipfile.ZipFile(jar_file, 'w')
    # Add files to the new JAR
    for f in ['%s-content.acp' % baseName, '%s-people.acp' % baseName, '%s-users.acp' % baseName, '%s-groups.txt' % baseName]:
        if os.path.exists(temppath + os.sep + f):
            # TODO Hard-coded package structure for now
            jarFile.write(temppath + os.sep + f, 'alfresco/bootstrap/sample-sites/%s' % (f))
    
    # Copy sample Spring config
    beanXMLPath = temppath + os.sep + ('sample-site-%s-context.xml') % (sd['shortName'])
    beanXMLFile = open('sample-bootstrap-site.xml', 'r')
    xmlText = beanXMLFile.read().replace('{siteName}', sd['shortName']).replace('{fileBase}', 'alfresco/bootstrap/sample-sites/%s' % (baseName))
    beanXMLFile.close()
    beanXMLFile = open(beanXMLPath, 'w')
    beanXMLFile.write(xmlText)
    beanXMLFile.close()
    # Add XML file to JAR file
    jarFile.write(beanXMLPath, 'alfresco/extension/sample-site-%s-context.xml' % (str(sd['shortName'])))
    
    # Close the JAR file
    jarFile.close()
    
    # Tidy up temp files
    shutil.rmtree(temppath)
    
    print('Done')

def getSiteUsers(siteData, usersFile, userNames=None):
    users = []
    if usersFile is not None:
        udata = json.loads(open(usersFile, 'r').read())['people']
    for m in siteData['memberships']:
        # Check user is on the export list or no users specified, plus they are a user (not a group!)
        if (userNames is None or str(m['authority']['userName']) in userNames) and m['authority']['authorityType'] == 'USER':
            # Try to look up the user
            for u in udata:
                if u['userName'] == m['authority']['userName']:
                    users.append(u)
    return users

def generatePeopleACP(fileName, siteData, usersFile, temppath, userNames=None):
    
    # Make the people ACP working directory
    extractpath = '%s/people' % (temppath)
    os.mkdir(extractpath)
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = os.path.splitext(fileName)[0]
    
    os.mkdir(extractpath + os.sep + fileBase)
    
    allfiles = []
    users = getSiteUsers(siteData, usersFile, userNames)
    
    # People ACP
    viewEl = generateViewXML({'{%s}exportOf' % (URI_REPOSITORY_1_0): '/sys:system/sys:people'})
    for u in users:
        personEl = generatePersonXML(viewEl, u)
        # User rich text description
        userDesc = u.get('persondescription')
        if userDesc is not None and userDesc != '':
            userDescAcpPath = fileBase + '/' + '%s-userDescription' % (str(u['userName']))
            userDescFile = open(extractpath + os.sep + userDescAcpPath.replace('/', os.sep), 'w')
            userDescFile.write(json.dumps(userDesc))
            userDescFile.close()
            generatePropertyXML(personEl.find('view:properties', NSMAP), '{%s}persondescription' % (URI_CONTENT_1_0), generateContentURL(userDescAcpPath, extractpath, mimetype='application/octet-stream'))
            allfiles.append(userDescAcpPath)
        # Add JSON prefs
        userPrefs = u.get('preferences')
        if userPrefs is not None and len(userPrefs) > 0:
            prefsAcpPath = fileBase + '/' + '%s-preferenceValues.json' % (str(u['userName']))
            prefsFile = open(extractpath + os.sep + prefsAcpPath.replace('/', os.sep), 'w')
            prefsFile.write(json.dumps(userPrefs))
            prefsFile.close()
            generatePropertyXML(personEl.find('view:properties', NSMAP), '{%s}preferenceValues' % (URI_CONTENT_1_0), generateContentURL(prefsAcpPath, extractpath, mimetype='text/plain'))
            allfiles.append(prefsAcpPath)
        # Avatar
        usersFileDir = os.path.dirname(usersFile)
        avatarPath = str(u.get('avatar', ''))
        if avatarPath != '':
            print "Adding profile image for user '%s'" % (u['userName'])
            avatarName = os.path.basename(avatarPath)
            shutil.copy(usersFileDir + os.sep + avatarPath, extractpath + os.sep + fileBase)
            avatarAcpPath = fileBase + '/' +  avatarName
            allfiles.append(avatarAcpPath)
            # Add cm:preferenceImage assoc
            preferenceImg = generateXMLElement(personEl.find('view:associations', NSMAP), '{%s}preferenceImage' % (URI_CONTENT_1_0))
            content = generateXMLElement(preferenceImg, '{%s}content' % (URI_CONTENT_1_0), {'{%s}childName' % (URI_REPOSITORY_1_0): avatarName})
            generateAspectsXML(content, [
                '{%s}auditable' % (URI_CONTENT_1_0), 
                '{%s}referenceable' % (URI_SYSTEM_1_0), 
                '{http://www.alfresco.org/model/rendition/1.0}renditioned'
            ])
            generatePropertiesXML(content, {
                '{%s}name' % (URI_CONTENT_1_0): avatarName,
                '{%s}contentPropertyName' % (URI_CONTENT_1_0): '{%s}content' % (URI_CONTENT_1_0),
                '{%s}content' % (URI_CONTENT_1_0): generateContentURL(avatarAcpPath, extractpath)
            })
            generateReferenceXML(viewEl, 'cm:%s' % (u['userName']), ['cm:%s/cm:%s' % (u['userName'], avatarName)], '{%s}avatar' % (URI_CONTENT_1_0))
    
    # Output the XML
    xmlPath = extractpath + os.sep + '%s.xml' % (fileBase)
    xmlFile = open(xmlPath, 'w')
    xmlFile.write(etree.tostring(viewEl, encoding='UTF-8'))
    xmlFile.close()
    
    # Build ACP file
    acpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w')
    # Add files to the new ZIP
    acpFile.write(xmlPath, '%s.xml' % (fileBase))
    for f in allfiles:
        acpFile.write(extractpath + os.sep + f.replace('/', os.sep), f)
    acpFile.close()

def generateContentURL(path, basePath, mimetype=None, size=None, encoding='UTF-8', clocale=None):
    if mimetype is None:
        mimetype = mimetypes.guess_type(path)[0]
    if mimetype == 'image/pjpeg':
        mimetype = 'image/jpeg'
    if size is None:
        size = os.path.getsize(basePath + os.sep + path.replace('/', os.sep))
    if clocale is None:
        clocale = DEFAULT_LOCALE
    return 'contentUrl=%s|mimetype=%s|size=%s|encoding=%s|locale=%s_' % (path, mimetype, size, encoding, clocale)

def generatePersonXML(parent, userData):
    userName = userData['userName']
    person = generateXMLElement(parent, '{%s}person' % (URI_CONTENT_1_0), attrs={'{%s}childName' % (URI_REPOSITORY_1_0): 'cm:%s' % (userName)})
    aspects = [
        '{%s}ownable' % (URI_CONTENT_1_0), 
        '{%s}referenceable' % (URI_SYSTEM_1_0), 
        '{%s}preferences' % (URI_CONTENT_1_0)
    ]
    if userData['enabled']:
        aspects.append('{%s}personDisabled' % (URI_CONTENT_1_0))
    properties = {
        '{%s}companyaddress1' % (URI_CONTENT_1_0): userData['companyaddress1'],
        '{%s}companyaddress2' % (URI_CONTENT_1_0): userData['companyaddress2'],
        '{%s}companyaddress3' % (URI_CONTENT_1_0): userData['companyaddress3'],
        '{%s}companyemail' % (URI_CONTENT_1_0): userData['companyemail'],
        '{%s}companyfax' % (URI_CONTENT_1_0): userData['companyfax'],
        '{%s}companypostcode' % (URI_CONTENT_1_0): userData['companypostcode'],
        '{%s}companytelephone' % (URI_CONTENT_1_0): userData['companytelephone'],
        '{%s}email' % (URI_CONTENT_1_0): userData['email'],
        '{%s}firstName' % (URI_CONTENT_1_0): userData['firstName'],
        '{%s}googleusername' % (URI_CONTENT_1_0): userData['googleusername'],
        '{%s}homeFolder' % (URI_CONTENT_1_0): '/app:company_home/app:user_homes/cm:%s' % (userName),
        '{%s}instantmsg' % (URI_CONTENT_1_0): userData['instantmsg'],
        '{%s}jobtitle' % (URI_CONTENT_1_0): userData['jobtitle'],
        '{%s}lastName' % (URI_CONTENT_1_0): userData['lastName'],
        '{%s}location' % (URI_CONTENT_1_0): userData['location'],
        '{%s}mobile' % (URI_CONTENT_1_0): userData['mobile'],
        '{%s}organization' % (URI_CONTENT_1_0): userData['organization'],
        '{%s}owner' % (URI_CONTENT_1_0): userName,
        '{%s}sizeCurrent' % (URI_CONTENT_1_0): str(userData['sizeCurrent']),
        '{%s}sizeQuota' % (URI_CONTENT_1_0): str(userData['quota']),
        '{%s}skype' % (URI_CONTENT_1_0): userData['skype'],
        '{%s}telephone' % (URI_CONTENT_1_0): userData['telephone'],
        '{%s}userName' % (URI_CONTENT_1_0): userName,
    }
    perms = [
        {'authority': userName, 'permission': 'All'},
        {'authority': 'ROLE_OWNER', 'permission': 'All'}
    ]
    
    generateACLXML(person, perms, True)
    generateAspectsXML(person, aspects)
    generatePropertiesXML(person, properties)
    generateAssociationsXML(person)
    
    return person

def generateUsersACP(fileName, siteData, usersFile, temppath, userNames=None):
    
    # Make the people ACP working directory
    extractpath = '%s/users' % (temppath)
    os.mkdir(extractpath)
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = os.path.splitext(fileName)[0]
    
    os.mkdir(extractpath + os.sep + fileBase)
    
    allfiles = []
    users = getSiteUsers(siteData, usersFile, userNames)
    
    # Users ACP
    viewEl = generateViewXML({'{%s}exportOf' % (URI_REPOSITORY_1_0): '/sys:system/sys:people'})
    for u in users:
        userEl = generateUserXML(viewEl, u)
    
    # Output the XML
    xmlPath = extractpath + os.sep + '%s.xml' % (fileBase)
    xmlFile = open(xmlPath, 'w')
    xmlFile.write(etree.tostring(viewEl, encoding='UTF-8'))
    xmlFile.close()
    
    # Build ACP file
    acpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w')
    # Add files to the new ZIP
    acpFile.write(xmlPath, '%s.xml' % (fileBase))
    for f in allfiles:
        acpFile.write(extractpath + os.sep + f.replace('/', os.sep), f)
    acpFile.close()

def generateGroupsData(fileName, siteData, usersFile, temppath, userNames=None):
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = os.path.splitext(fileName)[0]
    
    users = getSiteUsers(siteData, usersFile, userNames)
    
    # Groups file. A user is listed per-line along with the groups they are a member of, e.g. alice=group1
    groupsText = ''
    for u in users:
        groupNames = []
        if 'groups' in u:
            for g in u['groups']:
                groupNames.append(g['itemName'])
        # Look through site member data and add the right group
        for m in siteData['memberships']:
            if m['authority']['userName'] == u['userName'] and m['authority']['authorityType'] == 'USER':
                groupNames.append('GROUP_site_%s_%s' % (siteId, str(m['role'])))
        groupsText = groupsText + '%s=%s' % (u['userName'], ','.join(groupNames)) + "\n"
    
    # Output the text
    txtPath = temppath + os.sep + '%s.txt' % (fileBase)
    txtFile = open(txtPath, 'w')
    txtFile.write(groupsText)
    txtFile.close()

def generateUserXML(parent, userData):
    userName = str(userData['userName'])
    # Default to username if password not supplied
    password = userData.get('password') or userName
    md4hash = hashlib.new('md4', password.encode('utf-16le')).hexdigest()
    user = generateXMLElement(parent, '{%s}user' % (URI_USER_1_0), attrs={'{%s}childName' % (URI_REPOSITORY_1_0): 'usr:%s' % (userName)})
    aspects = [
        '{%s}referenceable' % (URI_SYSTEM_1_0)
    ]
    properties = {
        '{%s}name' % (URI_CONTENT_1_0): userData['userName'],
        '{%s}enabled' % (URI_USER_1_0): str(userData['enabled']).lower(),
        '{%s}password' % (URI_USER_1_0): str(md4hash),
        '{%s}username' % (URI_USER_1_0): userData['userName'],
        '{%s}salt' % (URI_USER_1_0): None,
        '{%s}credentialsExpire' % (URI_USER_1_0): 'false',
        '{%s}accountExpires' % (URI_USER_1_0): 'false',
        '{%s}accountLocked' % (URI_USER_1_0): 'false'
    }
    generateAspectsXML(user, aspects)
    generatePropertiesXML(user, properties)
    return user

def generateContentACP(fileName, siteData, jsonFileName, temppath, includeContent, siteContainers):
    """Generate an ACP file containing all the site contents and metadata"""
    # TODO Override the st:site/view:properties/cm:tagScopeCache value
    
    # Make the ACP working directory
    extractpath = temppath + os.sep + 'acp'
    os.mkdir(extractpath)
    
    filenamenoext = os.path.splitext(os.path.split(jsonFileName)[1])[0]
    thisdir = os.path.dirname(jsonFileName)
    if thisdir == "":
        thisdir = "."
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = os.path.splitext(fileName)[0]
    os.mkdir(extractpath + os.sep + fileBase)
    
    siteXML = generateSiteXML(siteData)
    allfiles = []
    siteTagCounts = []
    # Extract component ACP files
    if includeContent:
        containsEl = siteXML.find('st:site/view:associations/cm:contains', NSMAP)
        
        for container in siteContainers:
            acpFile = thisdir + os.sep + '%s-%s.acp' % (filenamenoext, container.replace(' ', '_'))
            acpXMLFile = '%s-%s.xml' % (filenamenoext, container.replace(' ', '_'))
            acpContentDir = '%s-%s' % (filenamenoext, container.replace(' ', '_'))
            if os.path.isfile(acpFile):
                print "Extract %s content" % (container)
                acpZip = zipfile.ZipFile(acpFile, 'r')
                try:
                    acpZip.extract(acpXMLFile, extractpath)
                except KeyError, e:
                    acpXMLFile = '%s.xml' % (container.replace(' ', '_'))
                    acpContentDir = '%s' % (container.replace(' ', '_'))
                    acpZip.extract(acpXMLFile, extractpath)
                containerEl = generateSiteContainerXML(containsEl, container)
                containerContainsEl = containerEl.find('view:associations/cm:contains', NSMAP)
                cviewEl = etree.parse('%s/%s' % (extractpath, acpXMLFile))
                for el in list(cviewEl.getroot()):
                    if not el.tag.startswith('{%s}' % (URI_REPOSITORY_1_0)):
                        # Add component folders to cm:contains el in the new XML
                        containerContainsEl.append(el)
                    elif el.tag == '{%s}reference' % (URI_REPOSITORY_1_0):
                        # Add to main file
                        # TODO Use generateReferenceXML, below
                        refEl = etree.Element('{%s}reference' % (URI_REPOSITORY_1_0))
                        fromref = el.get('{%s}pathref' % (URI_REPOSITORY_1_0))
                        if fromref is not None:
                            refEl.set('{%s}pathref' % (URI_REPOSITORY_1_0), fromref)
                            associations = etree.SubElement(refEl, '{%s}associations' % (URI_REPOSITORY_1_0))
                            references = etree.SubElement(associations, '{%s}references' % (URI_CONTENT_1_0))
                            refs = el.findall('view:associations/cm:references/view:reference', NSMAP)
                            for r in refs:
                                etree.SubElement(references, '{%s}reference' % (URI_REPOSITORY_1_0), {'{%s}pathref' % (URI_REPOSITORY_1_0): 'cm:%s/cm:%s/%s' % (siteId, container, r.get('{%s}pathref' % (URI_REPOSITORY_1_0)))})
                            siteXML.append(refEl)
                
                # Extract all files from the ACP file
                filelist = acpZip.namelist()
                extractlist = []
                for f in filelist:
                    # Filter out metadata XML file and any paths starting with a slash or other non-word character
                    if re.match('[\w\-]+/.+', f):
                        extractlist.append(f)
                acpZip.extractall(extractpath, extractlist)
                allfiles.extend(extractlist)
                
                acpZip.close()
                
                # Read component tags
                jsonFile = thisdir + os.sep + '%s-%s-tags.json' % (filenamenoext, container.replace(' ', '_'))
                tagCounts = []
                if os.path.isfile(jsonFile):
                    print "Import %s tags" % (container)
                    tagCounts = nodesTagCount(json.loads(open(jsonFile).read())['items'])
                # Add to site tag counts
                siteTagCounts = addTagCounts(siteTagCounts, tagCounts)
                tagScopePath = fileBase + '/' + '%s-tagScopeCache.bin' % (container.replace(' ', '_'))
                tagScopeFile = open(extractpath + os.sep + tagScopePath.replace('/', os.sep), 'w')
                tagScopeFile.write(generateTagScopeContent(tagCounts))
                tagScopeFile.close()
                generatePropertyXML(containerEl.find('view:properties', NSMAP), '{%s}tagScopeCache' % (URI_CONTENT_1_0), generateContentURL(tagScopePath, extractpath, mimetype='text/plain'))
                allfiles.append(tagScopePath)
        
        # Add site tagscope
        tagScopePath = fileBase + '/' + 'site-tagScopeCache.bin'
        tagScopeFile = open(extractpath + os.sep + tagScopePath.replace('/', os.sep), 'w')
        tagScopeFile.write(generateTagScopeContent(siteTagCounts))
        tagScopeFile.close()
        
        generatePropertyXML(siteXML.find('st:site/view:properties', NSMAP), '{%s}tagScopeCache' % (URI_CONTENT_1_0), generateContentURL(tagScopePath, extractpath, mimetype='text/plain'))
        allfiles.append(tagScopePath)
    
    # Output the XML
    siteXmlPath = extractpath + os.sep + '%s.xml' % (fileBase)
    siteXmlFile = open(siteXmlPath, 'w')
    siteXmlFile.write(etree.tostring(siteXML, encoding='UTF-8'))
    siteXmlFile.close()
    
    # Build ACP file
    siteAcpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w')
    # Add files to the new ZIP
    siteAcpFile.write(siteXmlPath, '%s.xml' % (fileBase))
    for f in allfiles:
        siteAcpFile.write('%s/%s' % (extractpath, f), f)
    siteAcpFile.close()

def nodesTagCount(nodeInfo):
    tagCounts = {}
    for node in nodeInfo:
        for tagName in node['tags']:
            tagCounts[tagName] = tagCounts.get(tagName, 0) + 1
    # Return array of tuples, ordered by tag count
    return tagCounts.items().sort(cmp=lambda x,y: cmp(y[1], x[1]))

def addTagCounts(count1, count2):
    """Add tag count 2 to tag count 1 and return the result. Each are tuples of tagname, count pairs"""
    tagCounts = {}
    for tag1 in count1:
        tagCounts[tag1[0]] = tagCounts.get(tag1[0], 0) + tag1[1]
    for tag2 in count2:
        tagCounts[tag2[0]] = tagCounts.get(tag2[0], 0) + tag2[2]
    # Return array of tuples, ordered by tag count
    return tagCounts.items().sort(cmp=lambda x,y: cmp(y[1], x[1])) or []

def generateTagScopeContent(counts):
    text = ''
    for item in counts:
        text = text + '%s|%d' % (item[0], item[1]) + "\n"
    return text

def generateReferenceXML(parent, fromRef, toRefs, refType='{%s}references' % (URI_CONTENT_1_0)):
    refEl = etree.SubElement(parent, '{%s}reference' % (URI_REPOSITORY_1_0))
    if fromRef is not None and toRefs is not None:
        refEl.set('{%s}pathref' % (URI_REPOSITORY_1_0), fromRef)
        associations = etree.SubElement(refEl, '{%s}associations' % (URI_REPOSITORY_1_0))
        references = etree.SubElement(associations, refType)
        for ref in toRefs:
            etree.SubElement(references, '{%s}reference' % (URI_REPOSITORY_1_0), {'{%s}pathref' % (URI_REPOSITORY_1_0): ref})

def generateSiteXML(siteData):
    siteId = siteData['shortName']
    # Register namespaces
    for (prefix, uri) in NSMAP.items():
        etree.register_namespace(prefix, uri)
    
    view = generateViewXML({'{%s}exportOf' % (URI_REPOSITORY_1_0): '/app:company_home/st:sites/cm:%s' % (siteId)})
    
    site = generateXMLElement(view, '{%s}site' % (URI_SITE_1_0))
    associations = generateAssociationsXML(site)
    contains = generateAssociationsContainsXML(associations)
    
    # Add aspects including sys:localized if not already present
    aspects = siteData['metadata']['aspects'] or []
    if '{%s}localized' % (URI_SYSTEM_1_0) not in aspects:
        aspects.append('{%s}localized' % (URI_SYSTEM_1_0))
    generateAspectsXML(site, aspects)
    
    # ACL
    perms = []
    for p in ['SiteConsumer', 'SiteCollaborator', 'SiteManager', 'SiteContributor']:
        perms.append({ 'authority': 'GROUP_site_%s_%s' % (siteId, p), 'permission': p})
    if siteData['visibility'] == 'PUBLIC':
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'ReadPermissions'})
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'SiteConsumer'})
    generateACLXML(site, perms, False)
    
    # Properties
    props = siteData['metadata']['properties']
    # Remove tagscope property from JSON, as we will populate this later
    props.pop('{%s}tagScopeCache' % (URI_CONTENT_1_0), None)
    props['{%s}tagScopeSummary' % (URI_CONTENT_1_0)] = []
    # Set locale if not already set
    props.setdefault('{%s}locale' % (URI_SYSTEM_1_0), '%s_' % (DEFAULT_LOCALE))
    # Turn title and description into mltext props
    props['{%s}title' % (URI_CONTENT_1_0)] = {DEFAULT_LOCALE: props.get('{%s}title' % (URI_CONTENT_1_0), '')}
    props['{%s}description' % (URI_CONTENT_1_0)] = {DEFAULT_LOCALE: props.get('{%s}description' % (URI_CONTENT_1_0), '')}
    generatePropertiesXML(site, props)
    
    return view

def generateViewXML(metadata):
    view = etree.Element('{%s}view' % (URI_REPOSITORY_1_0))
    metadata = etree.SubElement(view, '{%s}metadata' % (URI_REPOSITORY_1_0))
    for (k, v) in metadata.items():
        etree.SubElement(metadata, k).text = str(v)
    return view

def generateXMLElement(parent, tagName, attrs={}):
    return etree.SubElement(parent, tagName, attrs)

def generateAssociationsXML(parent):
    return generateXMLElement(parent, '{%s}associations' % (URI_REPOSITORY_1_0))

def generateAssociationsContainsXML(parent):
    return generateXMLElement(parent, '{%s}contains' % (URI_CONTENT_1_0))

def generateSiteContainerXML(parent, containerId):
    containerEl = etree.SubElement(parent, '{%s}folder' % (URI_CONTENT_1_0), attrib={'{%s}childName' % (URI_REPOSITORY_1_0): 'cm:%s' % (containerId)})
    associations = etree.SubElement(containerEl, '{%s}associations' % (URI_REPOSITORY_1_0))
    contains = etree.SubElement(associations, '{%s}contains' % (URI_CONTENT_1_0))
    # Aspects
    generateAspectsXML(containerEl, [
        '{%s}auditable' % (URI_CONTENT_1_0), 
        '{%s}ownable' % (URI_CONTENT_1_0), 
        '{%s}tagscope' % (URI_CONTENT_1_0), 
        '{%s}referenceable' % (URI_SYSTEM_1_0), 
        '{%s}titled' % (URI_CONTENT_1_0), 
        '{%s}localized' % (URI_SYSTEM_1_0)
    ])
    # Properties
    generatePropertiesXML(containerEl, {
        '{%s}name' % (URI_CONTENT_1_0): containerId,
        '{%s}title' % (URI_CONTENT_1_0): {DEFAULT_LOCALE: ''},
        '{%s}description' % (URI_CONTENT_1_0): {DEFAULT_LOCALE: ''},
        '{%s}componentId' % (URI_SITE_1_0): containerId,
        '{%s}locale' % (URI_SYSTEM_1_0): '%s_' % (DEFAULT_LOCALE),
        '{%s}tagScopeSummary' % (URI_CONTENT_1_0): []
    })
    return containerEl

def generateAspectsXML(parent, aspects):
    aspectsEl = etree.SubElement(parent, '{%s}aspects' % (URI_REPOSITORY_1_0))
    for aname in aspects:
        etree.SubElement(aspectsEl, aname)
    return aspectsEl

def generatePropertiesXML(parent, properties):
    propertiesEl = etree.SubElement(parent, '{%s}properties' % (URI_REPOSITORY_1_0))
    for (k, v) in properties.items():
        generatePropertyXML(propertiesEl, k, v)
    return propertiesEl

def generatePropertyXML(parent, key, value):
    propertyEl = etree.SubElement(parent, key)
    generatePropertyValueXML(propertyEl, value)
    return propertyEl

def generatePropertyValueXML(parentEl, value):
    if value is None:
        valuesEl = etree.SubElement(parentEl, '{%s}value' % (URI_REPOSITORY_1_0), {'{%s}isNull' % (URI_REPOSITORY_1_0): 'true'})
    elif isinstance(value, dict): # mltext
        for (lkey, lval) in value.items():
            etree.SubElement(parentEl, 
                '{%s}locale' % (URI_REPOSITORY_1_0),
                {'{%s}mlvalue' % (URI_REPOSITORY_1_0): lkey}
            ).text = unicode(lval)
    elif isinstance(value, list): # multi-value
        valuesEl = etree.SubElement(parentEl, '{%s}values' % (URI_REPOSITORY_1_0))
        for v in value:
            generatePropertyValueXML(etree.SubElement(parentEl, '{%s}value' % (URI_REPOSITORY_1_0)), v)
    elif isinstance(value, bool): # True or False
        parentEl.text = str(value).lower()
    else:
        parentEl.text = unicode(value)
    return parentEl

def generateACLXML(parent, permissions, inherit=False):
    aclEl = etree.SubElement(parent, '{%s}acl' % (URI_REPOSITORY_1_0), attrib={'{%s}inherit' % (URI_REPOSITORY_1_0): str(inherit).lower()})
    for p in permissions:
        generateACEXML(aclEl, p['authority'], p['permission'])
    return aclEl

def generateACEXML(parent, authority, permission, access='ALLOWED'):
    aceEl = etree.SubElement(parent, '{%s}ace' % (URI_REPOSITORY_1_0), attrib={'{%s}access' % (URI_REPOSITORY_1_0): access})
    etree.SubElement(aceEl, '{%s}authority' % (URI_REPOSITORY_1_0)).text = authority
    etree.SubElement(aceEl, '{%s}permission' % (URI_REPOSITORY_1_0)).text = permission
    return aceEl

if __name__ == "__main__":
    main(sys.argv[1:])
