#! /usr/bin/env python
# create-bootstrap-package.py

"""
Import a site definition and site content from the local file system.

Usage: python create-bootstrap-package.py file.jar [options]

Options and arguments:

file.jar                    Name of the JAR file to package information inside

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

# HTTP debugging flag
global _debug

def usage():
    print __doc__

def main(argv):

    filename = None
    users_file = ''
    groups_file = ''
    users = None
    siteContainers = [ 'documentLibrary', 'wiki', 'blog', 'calendar', 'discussions', 'links', 'dataLists', 'Saved Searches' ]
    includeContent = True
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            filename = argv[0]
    else:
        usage()
        sys.exit(1)
        
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "users-file=", "groups-file=", "site-file=", "containers=", "no-content"])
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
    
    if filename is None:
        print "No site file specified"
        sys.exit(1)
    
    filenamenoext = os.path.splitext(os.path.split(filename)[1])[0]
    thisdir = os.path.dirname(filename)
    if thisdir == "":
        thisdir = "."
    sd = json.loads(open(filename).read())
    
    # Temp working locations
    temppath = tempfile.mkdtemp(prefix='site-bootstrap-tmp-')
    
    # Generate the site ACP file - should generate ACP file in temppath
    generateContentACP(sd, filename, temppath, includeContent, siteContainers)
    
    # People ACP
    if users_file != '':
        generatePeopleACP(sd, users_file, temppath, users)
        generateUsersACP(sd, users_file, temppath, users)
        generateGroupsData(sd, users_file, temppath, users)
    else:
        print 'No user data supplied. Use --users-file=blah.json to include user info'
    
    # Build JAR file in current directory
    # TODO Support custom names for JAR files from the command line
    siteId = str(sd['shortName'])
    jarFile = zipfile.ZipFile('%s.jar' % (filenamenoext), 'w')
    # Add files to the new JAR
    for f in ['%s-content.acp' % siteId, '%s-people.acp' % siteId, '%s-users.acp' % siteId, '%s-groups.txt' % siteId]:
        if os.path.exists(temppath + os.sep + f):
            # TODO Hard-coded package structure for now
            jarFile.write(temppath + os.sep + f, '%s/%s' % ('alfresco/bootstrap/sample-sites', f))
            # TODO Auto-generate Spring config?
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

def generatePeopleACP(siteData, usersFile, temppath, userNames=None):
    
    # Make the people ACP working directory
    extractpath = '%s/people' % (temppath)
    os.mkdir(extractpath)
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = '%s-people' % (siteId)
    
    os.mkdir(extractpath + os.sep + fileBase)
    
    allfiles = []
    users = getSiteUsers(siteData, usersFile, userNames)
    
    # People ACP
    viewEl = generateViewXML({'{http://www.alfresco.org/view/repository/1.0}exportOf': '/sys:system/sys:people'})
    for u in users:
        personEl = generatePersonXML(viewEl, u)
        # User rich text description
        userDesc = u.get('persondescription')
        if userDesc is not None and userDesc != '':
            userDescAcpPath = fileBase + '/' + '%s-userDescription' % (str(u['userName']))
            userDescFile = open(extractpath + os.sep + userDescAcpPath.replace('/', os.sep), 'w')
            userDescFile.write(json.dumps(userDesc))
            userDescFile.close()
            generatePropertyXML(personEl.find('view:properties', NSMAP), '{http://www.alfresco.org/model/content/1.0}persondescription', generateContentURL(userDescAcpPath, extractpath, mimetype='application/octet-stream'))
            allfiles.append(userDescAcpPath)
        # Add JSON prefs
        userPrefs = u.get('preferences')
        if userPrefs is not None and len(userPrefs) > 0:
            prefsAcpPath = fileBase + '/' + '%s-preferenceValues.json' % (str(u['userName']))
            prefsFile = open(extractpath + os.sep + prefsAcpPath.replace('/', os.sep), 'w')
            prefsFile.write(json.dumps(userPrefs))
            prefsFile.close()
            generatePropertyXML(personEl.find('view:properties', NSMAP), '{http://www.alfresco.org/model/content/1.0}preferenceValues', generateContentURL(prefsAcpPath, extractpath, mimetype='text/plain'))
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
            preferenceImg = generateXMLElement(personEl.find('view:associations', NSMAP), '{http://www.alfresco.org/model/content/1.0}preferenceImage')
            content = generateXMLElement(preferenceImg, '{http://www.alfresco.org/model/content/1.0}content', {'{http://www.alfresco.org/view/repository/1.0}childName': avatarName})
            generateAspectsXML(content, [
                '{http://www.alfresco.org/model/content/1.0}auditable', 
                '{http://www.alfresco.org/model/system/1.0}referenceable', 
                '{http://www.alfresco.org/model/rendition/1.0}renditioned'
            ])
            generatePropertiesXML(content, {
                '{http://www.alfresco.org/model/content/1.0}name': avatarName,
                '{http://www.alfresco.org/model/content/1.0}contentPropertyName': '{http://www.alfresco.org/model/content/1.0}content',
                '{http://www.alfresco.org/model/content/1.0}content': generateContentURL(avatarAcpPath, extractpath)
            })
            generateReferenceXML(viewEl, 'cm:%s' % (u['userName']), ['cm:%s/cm:%s' % (u['userName'], avatarName)], '{http://www.alfresco.org/model/content/1.0}avatar')
    
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
        clocale = locale.getdefaultlocale(locale.LC_ALL)[0]
    return 'contentUrl=%s|mimetype=%s|size=%s|encoding=%s|locale=%s_' % (path, mimetype, size, encoding, clocale)

def generatePersonXML(parent, userData):
    userName = userData['userName']
    person = generateXMLElement(parent, '{http://www.alfresco.org/model/content/1.0}person', attrs={'{http://www.alfresco.org/view/repository/1.0}childName': 'cm:%s' % (userName)})
    aspects = [
        '{http://www.alfresco.org/model/content/1.0}ownable', 
        '{http://www.alfresco.org/model/system/1.0}referenceable', 
        '{http://www.alfresco.org/model/content/1.0}preferences'
    ]
    if userData['enabled']:
        aspects.append('{http://www.alfresco.org/model/content/1.0}personDisabled')
    properties = {
        '{http://www.alfresco.org/model/content/1.0}companyaddress1': userData['companyaddress1'],
        '{http://www.alfresco.org/model/content/1.0}companyaddress2': userData['companyaddress2'],
        '{http://www.alfresco.org/model/content/1.0}companyaddress3': userData['companyaddress3'],
        '{http://www.alfresco.org/model/content/1.0}companyemail': userData['companyemail'],
        '{http://www.alfresco.org/model/content/1.0}companyfax': userData['companyfax'],
        '{http://www.alfresco.org/model/content/1.0}companypostcode': userData['companypostcode'],
        '{http://www.alfresco.org/model/content/1.0}companytelephone': userData['companytelephone'],
        '{http://www.alfresco.org/model/content/1.0}email': userData['email'],
        '{http://www.alfresco.org/model/content/1.0}firstName': userData['firstName'],
        '{http://www.alfresco.org/model/content/1.0}googleusername': userData['googleusername'],
        '{http://www.alfresco.org/model/content/1.0}homeFolder': '/app:company_home/app:user_homes/cm:%s' % (userName),
        '{http://www.alfresco.org/model/content/1.0}instantmsg': userData['instantmsg'],
        '{http://www.alfresco.org/model/content/1.0}jobtitle': userData['jobtitle'],
        '{http://www.alfresco.org/model/content/1.0}lastName': userData['lastName'],
        '{http://www.alfresco.org/model/content/1.0}location': userData['location'],
        '{http://www.alfresco.org/model/content/1.0}mobile': userData['mobile'],
        '{http://www.alfresco.org/model/content/1.0}organization': userData['organization'],
        '{http://www.alfresco.org/model/content/1.0}sizeCurrent': str(userData['sizeCurrent']),
        '{http://www.alfresco.org/model/content/1.0}sizeQuota': str(userData['quota']),
        '{http://www.alfresco.org/model/content/1.0}skype': userData['skype'],
        '{http://www.alfresco.org/model/content/1.0}telephone': userData['telephone'],
        '{http://www.alfresco.org/model/content/1.0}userName': userName,
    }
    perms = [
        {'authority': userName, 'permission': 'All'},
        {'authority': 'ROLE_OWNER', 'permission': 'All'}
    ]
    # TODO Set cm:preferenceValues and cm:persondescription
    
    generateACLXML(person, perms, True)
    generateAspectsXML(person, aspects)
    generatePropertiesXML(person, properties)
    generateAssociationsXML(person)
    
    return person

def generateUsersACP(siteData, usersFile, temppath, userNames=None):
    
    # Make the people ACP working directory
    extractpath = '%s/users' % (temppath)
    os.mkdir(extractpath)
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = '%s-users' % (siteId)
    
    os.mkdir(extractpath + os.sep + fileBase)
    
    allfiles = []
    users = getSiteUsers(siteData, usersFile, userNames)
    
    # Users ACP
    viewEl = generateViewXML({'{http://www.alfresco.org/view/repository/1.0}exportOf': '/sys:system/sys:people'})
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

def generateGroupsData(siteData, usersFile, temppath, userNames=None):
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = '%s-groups' % (siteId)
    
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
    user = generateXMLElement(parent, '{http://www.alfresco.org/model/content/1.0}user', attrs={'{http://www.alfresco.org/view/repository/1.0}childName': 'usr:%s' % (userName)})
    aspects = [
        '{http://www.alfresco.org/model/system/1.0}referenceable'
    ]
    properties = {
        '{http://www.alfresco.org/model/user/1.0}enabled': str(userData['enabled']).lower(),
        '{http://www.alfresco.org/model/user/1.0}password': str(md4hash),
        '{http://www.alfresco.org/model/user/1.0}username': userData['userName'],
        '{http://www.alfresco.org/model/user/1.0}salt': None,
        '{http://www.alfresco.org/model/user/1.0}credentialsExpire': 'false',
        '{http://www.alfresco.org/model/user/1.0}accountExpires': 'false',
        '{http://www.alfresco.org/model/user/1.0}accountLocked': 'false'
    }
    generateAspectsXML(user, aspects)
    generatePropertiesXML(user, properties)
    return user

def generateContentACP(siteData, filename, temppath, includeContent, siteContainers):
    """Generate an ACP file containing all the site contents and metadata"""
    # TODO Override the st:site/view:properties/cm:tagScopeCache value
    
    # Make the ACP working directory
    extractpath = '%s/acp' % (temppath)
    os.mkdir(extractpath)
    
    filenamenoext = os.path.splitext(os.path.split(filename)[1])[0]
    thisdir = os.path.dirname(filename)
    if thisdir == "":
        thisdir = "."
    
    siteId = str(siteData['shortName'])
    # Base name for acp xml file and content folder
    fileBase = '%s-content' % (siteId)
    
    siteXML = generateSiteXML(siteData)
    allfiles = []
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
                cviewEl = etree.parse('%s/%s' % (extractpath, acpXMLFile))
                for el in list(cviewEl.getroot()):
                    if not el.tag.startswith('{http://www.alfresco.org/view/repository/1.0}'):
                        # Add component folder to cm:contains el in the new XML
                        containerEl.append(el)
                    elif el.tag == '{http://www.alfresco.org/view/repository/1.0}reference':
                        # Add to main file
                        # TODO Use generateReferenceXML, below
                        refEl = etree.Element('{http://www.alfresco.org/view/repository/1.0}reference')
                        fromref = el.get('{http://www.alfresco.org/view/repository/1.0}pathref')
                        if fromref is not None:
                            refEl.set('{http://www.alfresco.org/view/repository/1.0}pathref', fromref)
                            associations = etree.SubElement(refEl, '{http://www.alfresco.org/view/repository/1.0}associations')
                            references = etree.SubElement(associations, '{http://www.alfresco.org/model/content/1.0}references')
                            refs = el.findall('view:associations/cm:references/view:reference', NSMAP)
                            for r in refs:
                                etree.SubElement(references, '{http://www.alfresco.org/view/repository/1.0}reference', {'{http://www.alfresco.org/view/repository/1.0}pathref': 'cm:%s/cm:%s/%s' % (siteId, container, r.get('{http://www.alfresco.org/view/repository/1.0}pathref'))})
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

def generateReferenceXML(parent, fromRef, toRefs, refType='{http://www.alfresco.org/model/content/1.0}references'):
    refEl = etree.SubElement(parent, '{http://www.alfresco.org/view/repository/1.0}reference')
    if fromRef is not None and toRefs is not None:
        refEl.set('{http://www.alfresco.org/view/repository/1.0}pathref', fromRef)
        associations = etree.SubElement(refEl, '{http://www.alfresco.org/view/repository/1.0}associations')
        references = etree.SubElement(associations, refType)
        for ref in toRefs:
            etree.SubElement(references, '{http://www.alfresco.org/view/repository/1.0}reference', {'{http://www.alfresco.org/view/repository/1.0}pathref': ref})

def generateSiteXML(siteData):
    siteId = siteData['shortName']
    # Register namespaces
    for (prefix, uri) in NSMAP.items():
        etree.register_namespace(prefix, uri)
    
    view = generateViewXML({'{http://www.alfresco.org/view/repository/1.0}exportOf': '/app:company_home/st:sites/cm:%s' % (siteId)})
    
    site = generateXMLElement(view, '{http://www.alfresco.org/model/site/1.0}site')
    associations = generateAssociationsXML(site)
    contains = generateAssociationsContainsXML(associations)
    
    # Add aspects
    generateAspectsXML(site, siteData['metadata']['aspects'])
    #TODO Need to add '{http://www.alfresco.org/model/system/1.0}localized'?
    
    # ACL
    perms = []
    for p in ['SiteConsumer', 'SiteCollaborator', 'SiteManager', 'SiteContributor']:
        perms.append({ 'authority': 'GROUP_site_%s_%s' % (siteId, p), 'permission': p})
    if siteData['visibility'] == 'PUBLIC':
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'ReadPermissions'})
        perms.append({ 'authority': 'GROUP_EVERYONE', 'permission': 'SiteConsumer'})
    generateACLXML(site, perms, False)
    
    # Properties
    generatePropertiesXML(site, siteData['metadata']['properties'])
    
    return view

def generateViewXML(metadata):
    view = etree.Element('{http://www.alfresco.org/view/repository/1.0}view')
    metadata = etree.SubElement(view, '{http://www.alfresco.org/view/repository/1.0}metadata')
    for (k, v) in metadata.items():
        etree.SubElement(metadata, k).text = str(v)
    return view

def generateXMLElement(parent, tagName, attrs={}):
    return etree.SubElement(parent, tagName, attrs)

def generateAssociationsXML(parent):
    return generateXMLElement(parent, '{http://www.alfresco.org/view/repository/1.0}associations')

def generateAssociationsContainsXML(parent):
    return generateXMLElement(parent, '{http://www.alfresco.org/model/content/1.0}contains')

def generateSiteContainerXML(parent, containerId):
    containerEl = etree.SubElement(parent, '{http://www.alfresco.org/model/content/1.0}folder', attrib={'{http://www.alfresco.org/view/repository/1.0}childName': 'cm:%s' % (containerId)})
    associations = etree.SubElement(containerEl, '{http://www.alfresco.org/view/repository/1.0}associations')
    contains = etree.SubElement(associations, '{http://www.alfresco.org/model/content/1.0}contains')
    # Aspects
    generateAspectsXML(containerEl, [
        '{http://www.alfresco.org/model/content/1.0}auditable', 
        '{http://www.alfresco.org/model/content/1.0}ownable', 
        '{http://www.alfresco.org/model/content/1.0}tagscope', 
        '{http://www.alfresco.org/model/system/1.0}referenceable', 
        '{http://www.alfresco.org/model/content/1.0}titled', 
        '{http://www.alfresco.org/model/system/1.0}localized'
    ])
    # Properties
    generatePropertiesXML(containerEl, {
        '{http://www.alfresco.org/model/content/1.0}name': containerId,
        '{http://www.alfresco.org/model/content/1.0}title': '',
        '{http://www.alfresco.org/model/content/1.0}description': '',
        '{http://www.alfresco.org/model/content/1.0}tagScopeCache': '',
        '{http://www.alfresco.org/model/content/1.0}tagScopeSummary': [],
        '{http://www.alfresco.org/model/site/1.0}componentId': containerId,
        '{http://www.alfresco.org/model/system/1.0}locale': '%s_' % (locale.getdefaultlocale(locale.LC_ALL)[0]),
        '{http://www.alfresco.org/model/content/1.0}owner': 'admin',
        '{http://www.alfresco.org/model/content/1.0}tagScopeSummary': ''
    })
    return containerEl

def generateAspectsXML(parent, aspects):
    aspectsEl = etree.SubElement(parent, '{http://www.alfresco.org/view/repository/1.0}aspects')
    for aname in aspects:
        etree.SubElement(aspectsEl, aname)
    return aspectsEl

def generatePropertiesXML(parent, properties):
    propertiesEl = etree.SubElement(parent, '{http://www.alfresco.org/view/repository/1.0}properties')
    for (k, v) in properties.items():
        generatePropertyXML(propertiesEl, k, v)
    return propertiesEl

def generatePropertyXML(parent, key, value):
    propertyEl = etree.SubElement(parent, key)
    if key in ['{http://www.alfresco.org/model/content/1.0}title', '{http://www.alfresco.org/model/content/1.0}description']:
        etree.SubElement(propertyEl, 
            '{http://www.alfresco.org/view/repository/1.0}locale',
            {'{http://www.alfresco.org/view/repository/1.0}mlvalue': locale.getdefaultlocale(locale.LC_ALL)[0]}
        ).text = unicode(value)
    elif value is None:
        valuesEl = etree.SubElement(propertyEl, '{http://www.alfresco.org/view/repository/1.0}value', {'{http://www.alfresco.org/view/repository/1.0}isNull': 'true'})
    elif isinstance(value, list):
        valuesEl = etree.SubElement(propertyEl, '{http://www.alfresco.org/view/repository/1.0}values')
        for v in value:
            etree.SubElement(propertyEl, '{http://www.alfresco.org/view/repository/1.0}value').text = str(v)
    else:
        propertyEl.text = unicode(value)
    return propertyEl

def generateACLXML(parent, permissions, inherit=False):
    aclEl = etree.SubElement(parent, '{http://www.alfresco.org/view/repository/1.0}acl', attrib={'{http://www.alfresco.org/view/repository/1.0}inherit': str(inherit).lower()})
    for p in permissions:
        generateACEXML(aclEl, p['authority'], p['permission'])
    return aclEl

def generateACEXML(parent, authority, permission, access='ALLOWED'):
    aceEl = etree.SubElement(parent, '{http://www.alfresco.org/view/repository/1.0}ace', attrib={'{http://www.alfresco.org/view/repository/1.0}access': access})
    etree.SubElement(aceEl, '{http://www.alfresco.org/view/repository/1.0}authority').text = authority
    etree.SubElement(aceEl, '{http://www.alfresco.org/view/repository/1.0}permission').text = permission
    return aceEl

if __name__ == "__main__":
    main(sys.argv[1:])
