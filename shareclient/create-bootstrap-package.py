#! /usr/bin/env python
# create-bootstrap-package.py

"""
Package up a site bootstrap package for installation directly on an Alfresco 
server, using information from a local site definition. The package is 
generated as as JAR file, complete with a Spring configuration file to declare
appropriate beans to bootstrap the site definition when Alfresco is next started.

Once generated, the JAR file can be placed in tomcat/shared/lib or tomcat/lib
in your Alfresco installation.

Usage: python create-bootstrap-package.py site-file.json package-file.jar [options]

Options and arguments:

site-file.json              Name of the JSON file to read site data from

package-file.jar            Name of the JAR file to package information inside

--create-missing-members    Auto-create any members who do not exist in the 
                            repository

--site-file                 Local file name to read site information from in 
                            JSON format. Site information and content will be 
                            repackaged into a single ACP file.

--users-file=userfile.json  Local file name to read user information from in 
                            JSON format. User information will be repackaged 
                            into ACP format before being placed inside the JAR.
                            (Required)

--users=list                Comma-separated list of user names to include
                            in the user data, optional

--containers=list           Comma-separated list of container names to include
                            in the site content, e.g. documentLibrary,wiki

--content-path              Path inside the JAR file where content files should
                            be placed. Default is 'alfresco/bootstrap/
                            sample-sites'.

--no-content                Do not include site content in the content ACP, 
                            just create the site container itself 

--config-path               Path inside the JAR file to the auto-generated 
                            Spring configuration file, used to bootstrap the 
                            site on  first load. Default is 'alfresco/
                            extension/sample-site-%(siteId)s-context.xml', 
                            where standard Python string formatting is used to
                            inject the site ID (or URL name) into the file 
                            name.

--no-config                 Do not generate Spring configuration to place in
                            the JAR file

--config-depends            Advanced parameter for setting Spring bean 
                            dependencies

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
from xml.sax.saxutils import escape
from datetime import datetime
import uuid
from xml.sax.saxutils import escape

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
    includeConfig = True
    configPath = 'alfresco/extension/sample-site-%(siteId)s-context.xml'
    configDepends = ''
    contentPath = 'alfresco/bootstrap/sample-sites'
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
        opts, args = getopt.getopt(argv[2:], "hdu:p:U:", ["help", "users-file=", "users=", "groups-file=", "site-file=", "containers=", "no-content", "no-config", "config-path=", "config-depends=", "content-path="])
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
        elif opt == '--users':
            users = arg.split(',')
        elif opt == '--groups-file':
            groups_file = arg
        elif opt == '--containers':
            siteContainers = arg.split(',')
        elif opt == '--no-content':
            includeContent = False
        elif opt == '--no-config':
            includeConfig = False
        elif opt == '--config-depends':
            configDepends = arg.split(',')
        elif opt == '--config-path':
            configPath = arg
        elif opt == '--content-path':
            contentPath = arg
    
    if site_file is None:
        print "No site file specified"
        sys.exit(1)
    
    if users_file == '':
        print "No users file specified. Use --users-file=myfile.json to include user information."
        sys.exit(1)
    
    filenamenoext = os.path.splitext(os.path.split(site_file)[1])[0]
    thisdir = os.path.dirname(site_file)
    if thisdir == "":
        thisdir = os.path.dirname(sys.argv[0])
    sd = json.loads(open(site_file).read())
    
    # Temp working locations
    temppath = tempfile.mkdtemp(prefix='site-bootstrap-tmp-')
    
    baseName = os.path.splitext(os.path.basename(jar_file))[0]
    
    # Generate the site ACP file - should generate ACP file in temppath
    print 'Generating site structure and content'
    generateContentACP('%s-content.acp' % (baseName), sd, site_file, temppath, includeContent, siteContainers)
    
    # Person, user and group data
    print 'Generating person, user and group data'
    generatePeopleACP('%s-people.acp' % (baseName), sd, users_file, temppath, users)
    generateUsersACP('%s-users.acp' % (baseName), sd, users_file, temppath, users)
    generateGroupsData('%s-groups.txt' % (baseName), sd, users_file, temppath, None)
    
    print 'Building final JAR file'
    # Build JAR file in current directory
    jarFile = zipfile.ZipFile(jar_file, 'w', zipfile.ZIP_DEFLATED)
    # Create directories (must be done explicitly)
    for i in range(1, len(configPath.split('/'))):
        jarFile.write(temppath, '/'.join(configPath.split('/')[0:i]))
    for i in range(1, len(contentPath.split('/')) + 1):
        jarFile.write(temppath, '/'.join(contentPath.split('/')[0:i]))
    for f in ['%s-content.acp' % baseName, '%s-people.acp' % baseName, '%s-users.acp' % baseName, '%s-groups.txt' % baseName]:
        if os.path.exists(temppath + os.sep + f):
            jarFile.write(temppath + os.sep + f, '%s/%s' % (contentPath, f))
    
    # Copy sample Spring config
    if includeConfig:
        print 'Adding Spring configuration into %s' % (configPath % {'siteId': str(sd['shortName'])})
        beanXMLPath = temppath + os.sep + 'bootstrap-site-context.xml'
        beanXMLFile = open('sample-bootstrap-site.xml', 'r')
        xmlText = beanXMLFile.read() % {'siteId': sd['shortName'], 'contentBase': '%s/%s' % (contentPath, baseName)}
        beanXMLFile.close()
        # Add dependencies, if specified
        if configDepends != '':
            refsXml = ''
            for dep in configDepends:
                refsXml += '<ref bean="%s" />' % (escape(dep))
            #xmlText = xmlText.replace('depends=""', 'depends="%s"' % (escape(configDepends)))
            xmlText = xmlText.replace('</bean>', '<property name="dependsOn"><list>%s</list></property></bean>' % (refsXml))
        beanXMLFile = open(beanXMLPath, 'w')
        beanXMLFile.write(xmlText)
        beanXMLFile.close()
        # Add XML file to JAR file
        jarFile.write(beanXMLPath, configPath % {'siteId': str(sd['shortName'])})
    
    # Close the JAR file
    jarFile.close()
    
    # Tidy up temp files
    shutil.rmtree(temppath)
    
    print('')
    print('Built site package \'%s\' successfully. Drop this into tomcat/shared/lib in your Alfresco 4.0 instance and restart to import the site.' % (jar_file))

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
            generatePropertyXML(personEl.find('{%s}properties' % (URI_REPOSITORY_1_0)), '{%s}persondescription' % (URI_CONTENT_1_0), generateContentURL(userDescAcpPath, extractpath, mimetype='application/octet-stream'))
            allfiles.append(userDescAcpPath)
        # Add JSON prefs
        #userPrefs = u.get('preferences')
        #if userPrefs is not None and len(userPrefs) > 0:
        #    prefsAcpPath = fileBase + '/' + '%s-preferenceValues.json' % (str(u['userName']))
        #    prefsFile = open(extractpath + os.sep + prefsAcpPath.replace('/', os.sep), 'w')
        #    prefsFile.write(json.dumps(userPrefs))
        #    prefsFile.close()
        #    generatePropertyXML(personEl.find('{%s}properties' % (URI_REPOSITORY_1_0)), '{%s}preferenceValues' % (URI_CONTENT_1_0), generateContentURL(prefsAcpPath, extractpath, mimetype='text/plain'))
        #    allfiles.append(prefsAcpPath)
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
            preferenceImg = generateXMLElement(personEl.find('{%s}associations' % (URI_REPOSITORY_1_0)), '{%s}preferenceImage' % (URI_CONTENT_1_0))
            content = generateXMLElement(preferenceImg, '{%s}content' % (URI_CONTENT_1_0), {'{%s}childName' % (URI_REPOSITORY_1_0): 'cm:%s' % avatarName})
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
    acpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w', zipfile.ZIP_DEFLATED)
    # Add files to the new ZIP
    acpFile.write(xmlPath, '%s.xml' % (fileBase))
    for f in allfiles:
        acpFile.write(extractpath + os.sep + f.replace('/', os.sep), f)
    acpFile.close()

def generateContentURL(path, basePath, mimetype=None, size=None, encoding='UTF-8', clocale=None):
    if mimetype is None:
        mimetype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
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
    acpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w', zipfile.ZIP_DEFLATED)
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
    uid = str(uuid.uuid1())
    properties = {
        '{%s}name' % (URI_CONTENT_1_0): uid,
        '{%s}enabled' % (URI_USER_1_0): str(userData['enabled']).lower(),
        '{%s}password' % (URI_USER_1_0): str(md4hash),
        '{%s}username' % (URI_USER_1_0): userData['userName'],
        '{%s}salt' % (URI_USER_1_0): None,
        '{%s}credentialsExpire' % (URI_USER_1_0): 'false',
        '{%s}accountExpires' % (URI_USER_1_0): 'false',
        '{%s}accountLocked' % (URI_USER_1_0): 'false',
        '{%s}store-protocol' % (URI_SYSTEM_1_0): 'user',
        '{%s}store-identifier' % (URI_USER_1_0): 'alfrescoUserStore',
        '{%s}node-uuid' % (URI_USER_1_0): uid
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
    containsEl = siteXML.find('{%s}site/{%s}associations/{%s}contains' % (URI_SITE_1_0, URI_REPOSITORY_1_0, URI_CONTENT_1_0))
    if includeContent:
        for container in siteContainers:
            acpFile = thisdir + os.sep + '%s-%s.acp' % (filenamenoext, container.replace(' ', '_'))
            acpXMLFile = '%s-%s.xml' % (filenamenoext, container.replace(' ', '_'))
            acpContentDir = '%s-%s' % (filenamenoext, container.replace(' ', '_'))
            if os.path.isfile(acpFile):
                print "Adding %s content" % (container)
                acpZip = zipfile.ZipFile(acpFile, 'r')
                try:
                    acpZip.extract(acpXMLFile, extractpath)
                except KeyError, e:
                    acpXMLFile = '%s.xml' % (container.replace(' ', '_'))
                    acpContentDir = '%s' % (container.replace(' ', '_'))
                    acpZip.extract(acpXMLFile, extractpath)
                containerEl = generateSiteContainerXML(containsEl, container)
                containerContainsEl = containerEl.find('{%s}associations/{%s}contains' % (URI_REPOSITORY_1_0, URI_CONTENT_1_0))
                cviewEl = etree.parse('%s/%s' % (extractpath, acpXMLFile))
                for el in list(cviewEl.getroot()):
                    if not el.tag.startswith('{%s}' % (URI_REPOSITORY_1_0)):
                        # Add component folders to cm:contains el in the new XML
                        containerContainsEl.append(el)
                    elif el.tag == '{%s}reference' % (URI_REPOSITORY_1_0):
                        # Add to main file
                        # TODO Use generateReferenceXML, below
                        refBase = 'cm:%s/cm:%s' % (siteId, container)
                        refEl = etree.Element('{%s}reference' % (URI_REPOSITORY_1_0))
                        fromref = el.get('{%s}pathref' % (URI_REPOSITORY_1_0))
                        if fromref is not None:
                            refEl.set('{%s}pathref' % (URI_REPOSITORY_1_0), '%s/%s' % (refBase, fromref))
                            associations = etree.SubElement(refEl, '{%s}associations' % (URI_REPOSITORY_1_0))
                            references = etree.SubElement(associations, '{%s}references' % (URI_CONTENT_1_0))
                            refs = el.findall('{%s}associations/{%s}references/{%s}reference' % (URI_REPOSITORY_1_0, URI_CONTENT_1_0, URI_REPOSITORY_1_0))
                            for r in refs:
                                etree.SubElement(references, '{%s}reference' % (URI_REPOSITORY_1_0), {'{%s}pathref' % (URI_REPOSITORY_1_0): '%s/%s' % (refBase, r.get('{%s}pathref' % (URI_REPOSITORY_1_0)))})
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
                    print "Adding %s tags" % (container)
                    tagCounts = nodesTagCount(json.loads(open(jsonFile).read())['items'])
                # Add to site tag counts
                siteTagCounts = addTagCounts(siteTagCounts, tagCounts)
                # Persist
                tagScopePath = fileBase + '/' + '%s-tagScopeCache.bin' % (container.replace(' ', '_'))
                persistContent(generateTagScopeContent(tagCounts), extractpath, tagScopePath)
                generatePropertyXML(containerEl.find('{%s}properties' % (URI_REPOSITORY_1_0)), '{%s}tagScopeCache' % (URI_CONTENT_1_0), generateContentURL(tagScopePath, extractpath, mimetype='text/plain'))
                allfiles.append(tagScopePath)
        
        # Add site tagscope
        tagScopePath = fileBase + '/' + 'site-tagScopeCache.bin'
        persistContent(generateTagScopeContent(siteTagCounts), extractpath, tagScopePath)
        
        generatePropertyXML(siteXML.find('{%s}site/{%s}properties' % (URI_SITE_1_0, URI_REPOSITORY_1_0)), '{%s}tagScopeCache' % (URI_CONTENT_1_0), generateContentURL(tagScopePath, extractpath, mimetype='text/plain'))
        allfiles.append(tagScopePath)
        
    # Add page names if not specified in JSON, required for building site config
    pageNames = {'documentlibrary': 'Document Library', 'wiki-page': 'Wiki', 'discussions-topiclist': 'Discussions',
                 'blog-postlist': 'Blog', 'data-lists': 'Data Lists', 'links': 'Links', 'rmsearch': 'Saved Searches'}
    for p in siteData['sitePages']:
        if 'sitePageTitle' not in p:
            p['sitePageTitle'] = pageNames.get(str(p['pageId']).lower(), p['pageId'])
    
    # Add site configuration
    allfiles.extend(generateSiteConfigXML(siteData, containsEl, extractpath, fileBase))
    
    # Output the XML
    siteXmlPath = extractpath + os.sep + '%s.xml' % (fileBase)
    siteXmlFile = open(siteXmlPath, 'w')
    siteXmlFile.write(etree.tostring(siteXML, encoding='UTF-8'))
    siteXmlFile.close()
    
    # Build ACP file
    siteAcpFile = zipfile.ZipFile(temppath + os.sep + '%s.acp' % (fileBase), 'w', zipfile.ZIP_DEFLATED)
    # Add files to the new ZIP
    siteAcpFile.write(siteXmlPath, '%s.xml' % (fileBase))
    for f in allfiles:
        siteAcpFile.write('%s/%s' % (extractpath, f), f)
    siteAcpFile.close()

def generateSiteConfigXML(siteData, containsEl, tempDir, fileBase):
    # Return the list of files added
    files = []
    configEl = generateFolderXML(containsEl, 'surf-config')
    siteEl = generateFolderXML(generateFolderXML(generateFolderXML(configEl, 'pages'), 'site'), siteData['shortName'])
    componentsEl = generateFolderXML(configEl, 'components')
    
    # Generate site dashboard XML
    dashboardXmlPath = fileBase + '/' + 'dashboard.xml'
    persistDashboardXML(siteData, tempDir, dashboardXmlPath)
    generateContentXML(siteEl, dashboardXmlPath, contentBasePath=tempDir)
    files.append(dashboardXmlPath)
    
    # Generate site components XML
    regionIds = []
    sourceId = siteData['dashboardConfig']['dashboardPage'] # e.g. site/branding/dashboard
    scope = 'page'
    for component in siteData['dashboardConfig']['dashlets']:
        guid = '%s.%s.%s' % (scope, component['regionId'], sourceId.replace('/', '~'))
        componentXmlPath = fileBase + '/' + guid + '.xml'
        persistComponentXML(component, sourceId, scope, tempDir, componentXmlPath)
        generateContentXML(componentsEl, componentXmlPath, contentBasePath=tempDir)
        files.append(componentXmlPath)
        regionIds.append(component['regionId'])
        
    mandatorycmpts = [('full-width-dashlet', '/components/dashlets/dynamic-welcome', {'dashboardType': 'site'}), 
                      ('navigation', '/components/navigation/collaboration-navigation', {}),
                      ('title', '/components/title/collaboration-title', {})]
    
    # Add mandatory regions where not yet added
    for region in mandatorycmpts:
        if region[0] not in regionIds:
            guid = '%s.%s.%s' % (scope, region[0], sourceId.replace('/', '~'))
            componentXmlPath = fileBase + '/' + guid + '.xml'
            component = {'regionId': region[0], 'url': region[1], 'config': region[2]}
            persistComponentXML(component, sourceId, scope, tempDir, componentXmlPath)
            generateContentXML(componentsEl, componentXmlPath, contentBasePath=tempDir)
            files.append(componentXmlPath)
    
    return files

def persistDashboardXML(siteData, baseDir, filePath):
    persistContent(etree.tostring(generateDashboardXML(siteData), encoding='UTF-8'), baseDir, filePath)

def persistComponentXML(component, sourceId, scope, baseDir, filePath):
    persistContent(etree.tostring(generateComponentXML(component, sourceId, scope), encoding='UTF-8'), baseDir, filePath)

def persistContent(content, baseDir, filePath):
    xmlFile = open(baseDir + os.sep + filePath.replace('/', os.sep), 'w')
    xmlFile.write(content)
    xmlFile.close()

def generateDashboardXML(siteData):
    pageEl = etree.Element('page')
    etree.SubElement(pageEl, 'title').text = 'Collaboration Site Dashboard'
    etree.SubElement(pageEl, 'title-id').text = 'page.siteDashboard.title'
    etree.SubElement(pageEl, 'description').text = 'Collaboration site\'s dashboard page'
    etree.SubElement(pageEl, 'description-id').text = 'page.siteDashboard.description'
    etree.SubElement(pageEl, 'authentication').text = 'user'
    etree.SubElement(pageEl, 'template-instance').text = str(siteData['dashboardConfig']['templateId'])
    etree.SubElement(pageEl, 'page-type-id').text = 'generic'
    etree.SubElement(etree.SubElement(pageEl, 'properties'), 'sitePages').text = json.dumps(siteData['sitePages'])
    return pageEl

def generateComponentXML(component, sourceId, scope='page'):
    guid = '%s.%s.%s' % (scope, component['regionId'], sourceId.replace('/', '~'))
    cEl = etree.Element('component')
    etree.SubElement(cEl, 'guid').text = guid
    etree.SubElement(cEl, 'scope').text = scope
    etree.SubElement(cEl, 'region-id').text = component['regionId']
    etree.SubElement(cEl, 'source-id').text = sourceId
    etree.SubElement(cEl, 'url').text = component['url']
    propsEl = etree.SubElement(cEl, 'properties')
    for (k, v) in component.get('config', {}).items():
        etree.SubElement(propsEl, k).text = v
    return cEl

def nodesTagCount(nodeInfo):
    tagCounts = {}
    for node in nodeInfo:
        for tagName in node['tags']:
            tagCounts[tagName] = tagCounts.get(tagName, 0) + 1
    # Return array of tuples, ordered by tag count
    items = tagCounts.items()
    items.sort(key=lambda item: item[1], reverse=True)
    return items

def addTagCounts(count1, count2):
    """Add tag count 2 to tag count 1 and return the result. Each are tuples of tagname, count pairs"""
    tagCounts = {}
    for tag1 in count1:
        tagCounts[tag1[0]] = tagCounts.get(tag1[0], 0) + tag1[1]
    for tag2 in count2:
        tagCounts[tag2[0]] = tagCounts.get(tag2[0], 0) + tag2[1]
    # Return array of tuples, ordered by tag count
    items = tagCounts.items()
    items.sort(key=lambda item: item[1], reverse=True)
    return items

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
    if hasattr(etree, 'register_namespace'):
        for (prefix, uri) in NSMAP.items():
            etree.register_namespace(prefix, uri)
    else:
        print 'Warning: Default XML namespaces will but be used, Python 2.7 is required for this'
    
    view = generateViewXML({'{%s}exportOf' % (URI_REPOSITORY_1_0): '/app:company_home/st:sites/cm:%s' % (siteId)})
    aspects = []
    for aspect in siteData['metadata']['aspects'] or []:
        aspects.append(str(aspect))
    
    # ACL
    perms = []
    for p in ['SiteConsumer', 'SiteCollaborator', 'SiteManager', 'SiteContributor']:
        perms.append({ 'authority': 'GROUP_site_%s_%s' % (siteId, p), 'permission': p})
    if siteData['visibility'] == 'PUBLIC':
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'ReadPermissions'})
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'SiteConsumer'})
    
    # Properties
    props = {}
    for (k, v) in siteData['metadata']['properties'].items():
        props[str(k)] = v
    # Turn title and description into mltext
    props['{%s}title' % (URI_CONTENT_1_0)] = {DEFAULT_LOCALE: props.get('{%s}title' % (URI_CONTENT_1_0), '')}
    props['{%s}description' % (URI_CONTENT_1_0)] = {DEFAULT_LOCALE: props.get('{%s}description' % (URI_CONTENT_1_0), '')}
    # Remove tagscope property from JSON, as we will populate this later
    props.pop('{%s}tagScopeCache' % (URI_CONTENT_1_0), None)
    props['{%s}tagScopeSummary' % (URI_CONTENT_1_0)] = []
    # Convert dates
    convertDateProperties(props)
    
    site = generateFolderXML(view, siteId, '{%s}site' % (URI_SITE_1_0), aspects, props, perms, False)
    return view

def convertDateProperties(props):
    months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 
              'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    for (k, v) in props.items():
        if isinstance(v, (str, unicode)):
            m = re.match('(\w{3}) (\w{3}) (\d{1,2}) (\d+:\d+:\d+) (\w+) (\d{2,4})', str(v))
            if m: # e.g. Tue Jul 13 13:06:40 EDT 2010
                # Convert to 2011-02-15T20:16:27.080Z
                # TODO intepret using strftime() and strptime() - http://docs.python.org/library/datetime.html#strftime-strptime-behavior
                props[k] = '%04d-%02d-%02dT%s.000Z' % (int(str(m.group(6))), int(months[str(m.group(2))]), int(str(m.group(3))), str(m.group(4)))
    return props

def generateViewXML(metadata):
    view = etree.Element('{%s}view' % (URI_REPOSITORY_1_0))
    metadataEl = etree.SubElement(view, '{%s}metadata' % (URI_REPOSITORY_1_0))
    for (k, v) in metadata.items():
        etree.SubElement(metadataEl, str(k)).text = str(v)
    return view

def generateFolderXML(parent, childName, type='{%s}folder' % (URI_CONTENT_1_0), addaspects=[], addprops={}, perms=[], inheritPerms=True, addAssocs=True, addContains=True):
    return generateNodeXML(parent, childName, type, addaspects, addprops, perms, inheritPerms, addAssocs, addContains)

def generateContentXML(parent, contentPath, childName=None, type='{%s}content' % (URI_CONTENT_1_0), addaspects=[], addprops={}, perms=[], inheritPerms=True, addAssocs=False, addContains=False, contentBasePath='.'):
    if childName is None:
        childName = os.path.basename(contentPath)
    el = generateNodeXML(parent, childName, type, addaspects, addprops, perms, inheritPerms, addAssocs, addContains)
    if os.path.exists(contentBasePath + os.sep + contentPath.replace('/', os.sep)):
        contentURL = generateContentURL(contentPath, contentBasePath)
        generatePropertyXML(el, '{%s}content' % (URI_CONTENT_1_0), contentURL)
    return el

def generateNodeXML(parent, childName, type, addaspects=[], addprops={}, perms=[], inheritPerms=True, addAssocs=True, addContains=True):
    if parent.tag not in ['{%s}contains' % (URI_CONTENT_1_0), '{%s}view' % (URI_REPOSITORY_1_0)]:
        parent = parent.find('{%s}associations/{%s}contains' % (URI_REPOSITORY_1_0, URI_CONTENT_1_0))
    if parent is None:
        print "Error: could not find a suitable parent element"
        exit(1)
    folderEl = etree.SubElement(parent, type, attrib={'{%s}childName' % (URI_REPOSITORY_1_0): 'cm:%s' % (childName)})
    generateACLXML(folderEl, perms, inheritPerms)
    # Core aspects
    aspects = set([
        '{%s}auditable' % (URI_CONTENT_1_0), 
        '{%s}ownable' % (URI_CONTENT_1_0), 
        '{%s}referenceable' % (URI_SYSTEM_1_0), 
        '{%s}titled' % (URI_CONTENT_1_0), 
        '{%s}localized' % (URI_SYSTEM_1_0)
    ])
    aspects.union(addaspects)
    generateAspectsXML(folderEl, aspects)
    # Core properties
    props = {
        '{%s}name' % (URI_CONTENT_1_0): childName,
        '{%s}title' % (URI_CONTENT_1_0): {DEFAULT_LOCALE: ''},
        '{%s}description' % (URI_CONTENT_1_0): {DEFAULT_LOCALE: ''},
        '{%s}locale' % (URI_SYSTEM_1_0): '%s_' % (DEFAULT_LOCALE)
    }
    props.update(addprops)
    generatePropertiesXML(folderEl, props)
    # Contains assocs
    if addAssocs:
        associations = etree.SubElement(folderEl, '{%s}associations' % (URI_REPOSITORY_1_0))
    if addContains:
        contains = etree.SubElement(associations, '{%s}contains' % (URI_CONTENT_1_0))
    return folderEl

def generateXMLElement(parent, tagName, attrs={}):
    return etree.SubElement(parent, tagName, attrs)

def generateAssociationsXML(parent):
    return generateXMLElement(parent, '{%s}associations' % (URI_REPOSITORY_1_0))

def generateAssociationsContainsXML(parent):
    return generateXMLElement(parent, '{%s}contains' % (URI_CONTENT_1_0))

def generateSiteContainerXML(parent, containerId):
    return generateFolderXML(
        parent, 
        containerId, 
        addaspects=[
            '{%s}tagscope' % (URI_CONTENT_1_0)
        ], 
        addprops={
            '{%s}componentId' % (URI_SITE_1_0): containerId,
            '{%s}tagScopeSummary' % (URI_CONTENT_1_0): []
        }
    )

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
    if parent.tag != '{%s}properties' % (URI_REPOSITORY_1_0):
        parent = parent.find('{%s}properties' % (URI_REPOSITORY_1_0))
    propertyEl = etree.SubElement(parent, key)
    generatePropertyValueXML(propertyEl, value)
    return propertyEl

def generatePropertyValueXML(parentEl, value):
    if value is None:
        valuesEl = etree.SubElement(parentEl, '{%s}value' % (URI_REPOSITORY_1_0), {'{%s}isNull' % (URI_REPOSITORY_1_0): 'true'})
    elif isinstance(value, dict): # mltext
        for (lkey, lval) in value.items():
            etree.SubElement(parentEl, 
                '{%s}mlvalue' % (URI_REPOSITORY_1_0),
                {'{%s}locale' % (URI_REPOSITORY_1_0): lkey}
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
