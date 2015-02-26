#! /usr/bin/env python
# alfresco.py

"""This module provides a client implementation for connecting to, authenticating against and
performing operations against an Alfresco server.

Currently only a single main class ShareClient is defined by the module, which is designed to
mimic the action of a web browser in logging in to the Share application and performing actions.
"""

import cookielib
import json
import os
import re
import urllib
import urllib2
import sys

from xml.etree.ElementTree import XML

GUID_REGEXP = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{8}')
SHARE_CLIENT_USER_AGENT = 'ShareImportExport/1.0'
SIE_VERSION = 'Share Import-Export 1.3.0'
CSRF_TOKEN_NAME = 'Alfresco-CSRFToken'

class SurfRequest(urllib2.Request):
    """A request sent to a SpringSurf-based server. Adds support for additional method types in addition to GET and POST."""

    def __init__(self, url, data=None, headers={},
                 origin_req_host=None, unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
        self.http_method = method
    
    def get_method(self):
        if self.http_method is not None:
            return self.http_method
        else:
            return urllib2.Request.get_method(self)
    
    def set_method(self, method):
        self.http_method = method

class SurfRequestError(urllib2.HTTPError):
    """Error class for Surf Requests"""
    def __init__(self, method, url, code, msg, hdrs, fp):
        urllib2.HTTPError.__init__(self, url, code, msg, hdrs, fp)
        self.method = method
        self.respJSON = None
        self.description = ""
        self.exception = ""
        self.callstack = ""
        self.server = ""
        self.time = ""
        
        if ('Content-Type' in hdrs):
            self.respType = hdrs['Content-Type']
            try:
                self.respData = fp.read()
            except IOError, e:
                self.respData = ''
                pass
            if self.respType.startswith('application/json'):
                self.respJSON = json.loads(self.respData)
                self.description = self.respJSON['message']
                self.exception = self.respJSON['exception']
                self.callstack = self.respJSON['callstack']
                self.server = self.respJSON['server']
                self.time = self.respJSON['time']
    
    def __str__(self):
        if self.respJSON is not None:
            return 'Spring Surf Error %s (%s): "%s"' % (self.code, self.msg, self.description)
        else:
            return 'Spring Surf Error %s (%s)\n\n%s' % (self.code, self.msg, self.respData)
        
    def printCallStack(self):
        if isinstance(self.callstack, list) :
            for line in self.callstack:
                print str(line)

class ShareInstance:
    """Represents a running Alfresco Share application instance, identified by a URL"""

    def __init__(self, url):
        self.url = url.rstrip('/')

    def get_base_url(self):
        return self.url

    def get_url(self, path):
        return "%s/%s" % (self.get_base_url(), path)

class ShareTenant(ShareInstance):
    """Represents a particular tenant within a MT-enabled Share application"""

    def __init__(self, url, tenant):
        self.url = url.rstrip('/')
        self.tenant = tenant

    def get_base_url(self):
        return "%s/%s" % (self.url, self.tenant)

class ShareResponse:
    """Representation of a response received back from the Share application, may contain HTML or JSON or other data"""

    def __init__(self, response):
        """Create a new instance from urllib2 response data.

        The response can be a urllib2.HttpResponse or any file-like object (to facilitate testing)"""
        self.response = response
        self.status = None
        self.text = self.response.read()
        response.close()

    def __len__(self):
        return len(self.text)

    def get_text():
        return self.text

class JsonResponse(ShareResponse):
    """A JSON-format response received back from Share"""

    def __init__(self, response):
        ShareResponse.__init__(self, response)
        self.data = json.loads(self.text)

    def get_data(self):
        return self.data

class XmlResponse(ShareResponse):
    """A XML-format response received back from Share"""

    def __init__(self, response):
        ShareResponse.__init__(self, response)
        self.data = XML(self.text)

    def get_data(self):
        return self.data

class DashboardPageResponse(XmlResponse):
    """Reponse containing information on a Share dashboard, in XML format"""

    def get_site_pages(self):
        return json.loads(self.data.findtext('properties/sitePages', '[]'))

    def get_template_instance(self):
        return self.data.findtext('template-instance')

class DashletResponse(XmlResponse):
    """Reponse containing information on a Share dashlet, in XML format"""

    def dict(self):
        dashlet = {}
        dashlet['url'] = self.data.findtext('url')
        dashlet['regionId'] = self.data.findtext('region-id')
        
        p = self.data.find('properties')
        if p is not None:
            props = p.getchildren()
            if props:
                dprops = {}
                for p in props:
                    dprops[p.tag] = str(p.text)
                dashlet['config'] = dprops
        return dashlet

class ShareRequest:
    """Encapsulate a user request made to a Share instance"""

    def __init__(self, instance, path, data=None, dataType=None, method='GET', debug=0, timeout=300):
        self.instance = instance
        self.path = path
        self.data = data
        self.dataType = dataType
        self.method = method
        self.debug = debug
        self.timeout = timeout

    def execute(self, opener, resp_class=ShareResponse):
        """Execute the request using the given opener and return the response, wrapped within a ShareResponse object, 
        or an instance of the class specified.

        If a custom class is specified then this must implement an __init__ method which takes the response object from urllib.open() as an argument
        """
        req = SurfRequest(url=self.instance.get_url(self.path), data=self.data, method=self.method)
        if self.debug == 1:
            print "%s %s/%s" % (self.method, instance.get_url(), self.path)
        if self.dataType is not None:
            req.add_header('Content-Type', self.dataType)
        try:
            return resp_class(opener.open(req, timeout=self.timeout))
        except urllib2.HTTPError, e:
            raise SurfRequestError(self.method, e.url, e.code, e.msg, e.hdrs, e.fp)

class CSRFTokenHandler(urllib2.BaseHandler):
    """Adds the Alfresco-CSRFToken header to the requests for non-idempotent requests, if a value can be found in the cookie jar"""

    def __init__(self, cj):
        self.cj = cj or cookielib.CookieJar()

    def __get_token(self):
        for cookie in self.cj:
            if cookie.name == CSRF_TOKEN_NAME:
                return urllib.unquote(cookie.value)

    def http_request(self, req):
        if req.get_method() != 'GET':
            token = self.__get_token()
            if token is not None:
                req.add_header(CSRF_TOKEN_NAME, token)
        return req

class ShareClient:
    """Access Alfresco Share progamatically via its RESTful API"""

    def __init__(self, url="http://localhost:8080/share", tenant=None, debug=0, mplib='MultipartPostHandler', timeout=300):
        """Initialise the client"""
        self.cj = cookielib.CookieJar()
        headers = [
                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'), 
                   ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'), 
                   ('Accept-Language', 'en-gb,en;q=0.5'), 
                   ('User-Agent', SHARE_CLIENT_USER_AGENT)
        ]
        # Regular opener
        opener = urllib2.build_opener(urllib2.HTTPSHandler(debuglevel=debug), urllib2.HTTPHandler(debuglevel=debug), urllib2.HTTPCookieProcessor(self.cj), CSRFTokenHandler(self.cj))
        opener.addheaders = headers
        # Multipart opener
        if mplib == 'MultipartPostHandler':
            from MultipartPostHandler import MultipartPostHandler
            m_opener = urllib2.build_opener(MultipartPostHandler, urllib2.HTTPSHandler(debuglevel=debug), urllib2.HTTPHandler(debuglevel=debug), urllib2.HTTPCookieProcessor(self.cj), CSRFTokenHandler(self.cj))
        elif mplib == 'poster':
            import poster.streaminghttp
            m_opener = poster.streaminghttp.register_openers()
            m_opener.add_handler(urllib2.HTTPCookieProcessor(self.cj))
        else:
            raise Exception('Bad multipart library %s' % (mplib))
        m_opener.addheaders = headers
        
        self.url = url.rstrip('/')
        self.tenant = tenant
        self.opener = opener
        self.m_opener = m_opener
        self.debug = debug
        self._username = None
        self.mplib = mplib
        self.sitesContainer = None
        self.timeout = timeout
        self.instance = self.tenant and ShareTenant(self.url, self.tenant) or ShareInstance(self.url)

    def doRequest(self, method, path, data=None, dataType=None):
        """Perform a general HTTP request against Share"""
        reqbase = self.getRequestBase()
        url = "%s/%s" % (reqbase, path)
        req = SurfRequest(url=url, data=data, method=method)
        if self.debug == 1:
            print "%s %s/%s" % (method, reqbase, path)
        if dataType is not None:
            req.add_header('Content-Type', dataType)
        try:
            return self.opener.open(req, timeout=self.timeout)
        except urllib2.HTTPError, e:
            raise SurfRequestError(method, e.url, e.code, e.msg, e.hdrs, e.fp)

    def getRequestBase(self):
        """Return the base URL of the Share application"""
        return self.url if self.tenant is None else ("%s/%s" % (self.url, self.tenant))

    def doGet(self, path):
        """Perform a HTTP GET request against Share"""
        return self.doRequest("GET", path)

    def doPost(self, path, data="", dataType='application/x-www-form-urlencoded', method="POST"):
        """Perform a HTTP POST request against Share"""
        return self.doRequest(method, path, data, dataType)

    def doJSONGet(self, path):
        """Perform a HTTP GET request against Share and parse the output JSON data"""
        resp = self.doGet(path)
        respJson = json.loads(resp.read())
        resp.close()
        if 'status' in respJson and 'code' in respJson['status'] and respJson['status']['code'] > 399: # An error occurred
            raise SurfRequestError('GET', path, respJson['status']['code'], respJson['message'], [], None)
        return respJson

    def doJSONPost(self, path, data="", method="POST"):
        """Perform a HTTP POST request against Share and parse the output JSON data"""
        if isinstance(data, (dict)):
            dataStr = json.dumps(data)
        elif isinstance(data, (str, unicode)):
            dataStr = data
        else:
            raise Exception('Bad data type %s' % (type(data)))
        resp = self.doPost(path, dataStr, 'application/json; charset=UTF-8', method)
        jsonData = resp.read()
        resp.close()
        
        if self.debug == 1:
            print jsonData
        return json.loads(jsonData)
    
    def doMultipartUpload(self, path, params):
        """Perform a multipart form upload against Share"""
        reqbase = self.url if self.tenant is None else ("%s/%s" % (self.url, self.tenant))
        requrl = "%s/%s?%s=%s" % (reqbase, path, CSRF_TOKEN_NAME, urllib.quote(self._getCSRFToken()))
        try:
            if self.mplib == 'MultipartPostHandler':
                return self.m_opener.open(requrl, params)
            elif self.mplib == 'poster':
                import poster.encode
                datagen, headers = poster.encode.multipart_encode(params)
                request = urllib2.Request(requrl, datagen, headers)
                return self.m_opener.open(request)
        except urllib2.HTTPError, e:
            raise SurfRequestError("POST", e.url, e.code, e.msg, e.hdrs, e.fp)

    def _getCSRFToken(self):
        """Return the latest CSRF token for this session, from cookie data. Returns an empty string if no value is found."""
        for cookie in self.cj:
            if cookie.name == CSRF_TOKEN_NAME:
                return urllib.unquote(cookie.value)
        return ''


    # Session functions

    def doLogin(self, username, password):
        """Log in to Share via the login servlet"""
        pp = ('-default-/' if self.tenant is not None else '') + 'page' # page prefix
        successurl = '/share/%s/site-index' % (pp)
        failureurl = '/share/%s/type/login?error=true' % (pp)
        try:
            # Try 3.2 method first, which will fail on 3.3 and above
            resp = self.doPost('login', urllib.urlencode({'username': username, 'password': password, 'success': successurl, 'failure': failureurl}))
            if resp.geturl().endswith('/login'): # Cloud just returns the login page - need to try again
                resp = self.doPost('page/dologin', urllib.urlencode({'username': username, 'password': password, 'success': successurl, 'failure': failureurl}))
        except SurfRequestError, e:
            resp = self.doPost('page/dologin', urllib.urlencode({'username': username, 'password': password, 'success': successurl, 'failure': failureurl}))
        if (resp.geturl().endswith('/dashboard')):
            self._username = username
            resp.close()
            return { 'success': True }
        else:
            resp.close()
            return { 'success': False }

    def doLogout(self):
        """Log the current user out of Share using the logout servlet"""
        try:
            resp = self.doGet('page/dologout')
            resp.close()
        except SurfRequestError, e:
            if e.code == 405: # GET Method not allowed, must use POST for newer versions of Alfresco
            	try:
                    resp = self.doPost('page/dologout')
                except SurfRequestError, e:
                	if e.code == 401: # POST Method return not authorized, must use POST for newer versions of Alfresco
                		print "Logged out"
                	else:
                		print "Unknown error on logout, HTTP response: %s error: %s" % e.code, e.description
				resp.close()
        
        self._username = None
    
    def getSitesContainerName(self):
        if self.sitesContainer is None:
            json = self._getDocumentList('')
            for item in json['items']:
                if 'nodeType' in item and item['nodeType'] == 'st:sites':
                    self.sitesContainer = item['fileName']
        return self.sitesContainer

    def updateDashboardConfig(self, configData):
        """Update a Share dashboard configuration"""
        result = {}
        result['dashboard-results'] = self.doJSONPost('service/components/dashboard/customise-dashboard', json.dumps(configData))
        result['dashlet-results'] = {}
        for dashlet in configData['dashlets']:
            if 'config' in dashlet:
                dashletId = 'page.%s.%s' % (dashlet['regionId'], configData['dashboardPage'].replace('/', '~'))
                print 'Setting config for dashlet %s' % (dashletId)
                result['dashlet-results'][dashletId] = self.setDashletConfig(dashletId, dashlet['config'])
        return result
    
    def setDashletConfig(self, dashletId, configData):
        """Update the configuration of a specific dashlet
        
        dashletId is something like "page.component-3-2.site~PartnerES~dashboard" or "page.component-3-2.user~wabson~dashboard"
        configData is a dictionary object defining the values to update
        """
        return self.doJSONPost('service/modules/dashlet/config/%s' % (urllib.quote(unicode(dashletId))), json.dumps(configData))
    
    # User functions
    
    def setProfileImage(self, username, imgpath):
        """Upload and set a profile image for a Share user"""
        uparams = { 'filedata' : file(imgpath, 'rb'), 'siteid':'', 'containerid':'', 'destination':'', 'username':username, 'updateNodeRef':'', 'uploadDirectory':'', 'overwrite':'false', 'thumbnails':'', 'successCallback':'', 'successScope':'', 'failureCallback':'', 'failureScope':'', 'contentType':'cm:content', 'majorVersion':'false', 'description':'' }
        fr = self.doMultipartUpload("proxy/alfresco/slingshot/profile/uploadavatar", uparams)
        udata = json.loads(fr.read())
        if udata['status']['code'] == 200:
            nodeRef = udata['nodeRef']
            return self.doJSONPost('service/components/profile/userprofile', '{"template_x002e_user-profile_x002e_user-profile-photoref":"%s"}' % (nodeRef))
        else:
            raise Exception("Could not upload file (got status code %s)" % (udata['status']['code']))

    def updateUserDetails(self, user):
        """Update the profile information for the current Share user"""
        jsonData = re.sub('\\"([-\\w]+)\\"\\:', '"template_x002e_user-profile_x002e_user-profile-input-\\1":', json.dumps(user))
        # Could also use POST /alfresco/service/slingshot/profile/userprofile
        return self.doJSONPost('service/components/profile/userprofile', jsonData)

    def updateUserDashboardConfig(self, user):
        """Update the a dashboard configuration for the current Share user"""
        return self.updateDashboardConfig(user['dashboardConfig'])
    
    # Site functions
    
    def getSiteInfo(self, siteId, getMetaData=False, getMemberships=False, getPages=False, getDashboardConfig=False):
        """Get information about a site"""
        siteData = self.doJSONGet('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteId))))
        if getMetaData:
            siteNodeRef = '/'.join(siteData['node'].split('/')[5:]).replace('/', '://', 1)
            siteData['metadata'] = self.doJSONGet('proxy/alfresco/api/metadata?nodeRef=%s' % (siteNodeRef))
        if getMemberships:
            siteData['memberships'] = self.doJSONGet('proxy/alfresco/api/sites/%s/memberships' % (urllib.quote(unicode(siteId))))
        # Since there is no JSON API to GET the site dashboard configuration, we need to query the AVM
        # sitestore directly on the repository tier. As the queries are proxied through the web tier, 
        # this should still work even if the repository is running on a different server to Share.
        if getPages:
            try:
                dashboardResp = ShareRequest(self.instance, 'proxy/alfresco/remotestore/get/s/sitestore/alfresco/site-data/pages/site/%s/dashboard.xml' % (siteId)) \
                    .execute(self.opener, DashboardPageResponse)
            except SurfRequestError, e:
                # Try 4.0 method
                if e.code in (404, 500):
                    dashboardResp = ShareRequest(self.instance, 'proxy/alfresco/remoteadm/get/s/sitestore/alfresco/site-data/pages/site/%s/dashboard.xml' % (siteId)) \
                        .execute(self.opener, DashboardPageResponse)
                else:
                    raise e
            siteData['sitePages'] = dashboardResp.get_site_pages()
        if getDashboardConfig:
            siteData['dashboardConfig'] = self.getDashboardConfig('site', siteId)
        return siteData
    
    def getDashboardConfig(self, dashboardType, dashboardId):
        """
        Get information on a site or user dashboard
        
        dashboardType is either 'site' or 'user'
        dashboardId is the site or user ID
        """
        try:
            try:
                dashboardResp = ShareRequest(self.instance, 'proxy/alfresco/remotestore/get/s/sitestore/alfresco/site-data/pages/%s/%s/dashboard.xml' % \
                    (urllib.quote(unicode(dashboardType)), urllib.quote(unicode(dashboardId)))) \
                    .execute(self.opener, DashboardPageResponse)
            except SurfRequestError, e:
                # Try 4.0 method
                if e.code in (404, 500): # 4.0.a returns 500, 4.0.b returns 404
                    dashboardResp = ShareRequest(self.instance, 'proxy/alfresco/remoteadm/get/s/sitestore/alfresco/site-data/pages/%s/%s/dashboard.xml' % \
                        (urllib.quote(unicode(dashboardType)), urllib.quote(unicode(dashboardId)))) \
                        .execute(self.opener, DashboardPageResponse)
                else:
                    raise e
            templateInstance = dashboardResp.get_template_instance()
            dashlets = []
            urltmpl = 'proxy/alfresco/%s/get/s/sitestore/alfresco/site-data/components/page.component-%s-%s.%s~%s~dashboard.xml'
            # Iterate through dashboard components
            for i in [ 1, 2, 3 ]:
                for j in [ 1, 2, 3, 4 ]:
                    try:
                        try:
                            dashletResp = ShareRequest(self.instance, urltmpl % ('remotestore', i, j, urllib.quote(unicode(dashboardType)), urllib.quote(unicode(dashboardId)))) \
                                .execute(self.opener, DashletResponse)
                        except SurfRequestError, e:
                            if e.code in (404, 500):
                                dashletResp = ShareRequest(self.instance, urltmpl % ('remoteadm', i, j, urllib.quote(unicode(dashboardType)), urllib.quote(unicode(dashboardId)))) \
                                    .execute(self.opener, DashletResponse)
                            else:
                                raise e
                        dashlets.append(dashletResp.dict())
                    except SurfRequestError, e:
                        if e.code == 404:
                            pass
                        else:
                            raise e
            dashboardConfig = { 'dashboardPage': '%s/%s/dashboard' % (dashboardType, dashboardId), 'templateId': templateInstance, 'dashlets': dashlets }
        except SurfRequestError, e:
            if e.code == 404:
                dashboardConfig = None
            else:
                raise e
        return dashboardConfig
    
    def getSiteTags(self, siteId, componentId=""):
        """Get tagscope information on a site or site component"""
        tagData = self.doJSONGet(('proxy/alfresco/api/tagscopes/site/%s/%s/tags' % (urllib.quote(unicode(siteId)), urllib.quote(unicode(componentId)))).replace('//', '/'))
        return tagData
    
    def getSiteTagInfo(self, siteId, componentId=""):
        """Get information on each tagged document in the site"""
        nodeInfo = {}
        tagData = self.getSiteTags(siteId, componentId)
        tagName = ""
        for tag in tagData['tags']:
            tagName = tag['name']
            # Return all items matching this tag
            result = self.doJSONGet('proxy/alfresco/slingshot/search?site=%s&term=&tag=%s&maxResults=1000&sort=&query=&repo=false' % (urllib.quote(unicode(siteId)), urllib.quote(unicode(tagName))))
            for item in result['items']:
                if (item['container'] == componentId or componentId == "") and item['nodeRef'] not in nodeInfo:
                    itemPath = None
                    if 'path' in item:
                        itemPath = item['path']
                    else:
                        nodeJson = self.doJSONGet('proxy/alfresco/slingshot/doclib/node/%s' % (item['nodeRef'].replace('://', '/')))
                        itemPath = nodeJson['item']['location']['path'].strip('/')
                    if itemPath is None:
                        raise Exception("Could not determine path for node %s" % (item['nodeRef']))
                    nodeInfo[item['nodeRef']] = { 
                                                 'type': item['type'], 
                                                 'name': item['name'], 
                                                 'container': item['container'], 
                                                 'path': itemPath, 
                                                 'tags': item['tags']
                                                 }
        return nodeInfo.values()
    
    def createSite(self, siteData):
        """Create a Share site"""
        return self.doJSONPost('service/modules/create-site', json.dumps(siteData))
    
    def createRmSite(self, siteData):
        resp = self.doGet('service/utils/create-rmsite?shortname=%s' % (siteData['shortName']))
        resp.close()
        resp = self.doGet('page/site/%s/dashboard' % (siteData['shortName']))
        resp.close()
        print "Created RM site"
        self.updateSite(siteData)
    
    def updateSite(self, siteData):
        """Update a Share site"""
        return self.doJSONPost('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteData['shortName']))), json.dumps(siteData), method="PUT")
    
    def setSitePages(self, pageData):
        """Set the pages in a site
        
        pageData should be a dict object with keys 'pages', 'siteId' and (in 4.0) 'themeId'"""
        return self.doJSONPost('service/components/site/customise-pages', json.dumps(pageData))

    def updateSiteDashboardConfig(self, siteData):
        """Update the a dashboard configuration for a site"""
        return self.updateDashboardConfig(siteData['dashboardConfig'])

    def addSiteMember(self, siteName, memberData):
        """Add a site member"""
        # TODO Support group and person objects as well as authority, as per web script doc
        authorityName = memberData['authority']['fullName']
        try:
            # For 3.4 and under
            return self.doJSONPost('proxy/alfresco/api/sites/%s/memberships/%s' % (urllib.quote(unicode(siteName)), urllib.quote(unicode(authorityName))), json.dumps(memberData), method="PUT")
        except SurfRequestError, e:
            if e.code == 404:
                # For 4.0+
                return self.doJSONPost('proxy/alfresco/api/sites/%s/memberships' % (urllib.quote(unicode(siteName))), json.dumps(memberData), method="PUT")
            else:
                raise e

    def addSiteMembers(self, siteName, membersData, skipMissingMembers=False, createMissingMembers=False, authorityData=None):
        """Add one or more site members"""
        results = { 'membersAdded': [], 'membersCreated': [] }
        for m in membersData:
            try:
                results['membersAdded'].append({ 'member': m, 'result': self.addSiteMember(siteName, m)})
            except SurfRequestError, e:
                if skipMissingMembers == True:
                    pass
                elif createMissingMembers == True and m['authority']['authorityType'] == 'USER':
                    if authorityData['people'] is not None:
                        # Auto-create from people data
                        # TODO Throw an error if the user is not found in the data
                        for u in authorityData['people']:
                            if u['userName'] == m['authority']['userName']:
                                self.createUser(u)
                                results['membersCreated'].append({ 'member': m, 'person': u, 'result': self.addSiteMember(siteName, m)})
                    else:
                        # Auto-create user based on info in their membership
                        self.createUser(m['authority'])
                        results['membersCreated'].append({ 'member': m, 'result': self.addSiteMember(siteName, m)})
                elif createMissingMembers == True and m['authority']['authorityType'] == 'GROUP':
                    # Auto-create group based on info in their membership
                    # TODO Support creating non-root groups properly if defined in groups file
                    self.createGroup(m['authority']['shortName'], m['authority']['displayName'], None)
                    results['membersCreated'].append({ 'member': m, 'result': self.addSiteMember(siteName, m)})
                else:
                    raise e
        return results
    
    def deleteSite(self, site):
        """Remove a Share site
        
        site can be a string value containing the siteName identifier or a dictionary object"""
        if type(site) == str:
            siteData = { 'shortName': site }
        else:
            siteData = site
        # Site API does not remove web-tier components
        #return self.doJSONPost('proxy/alfresco/api/sites', json.dumps(siteData), method="DELETE")
        return self.doJSONPost('service/modules/delete-site', json.dumps(siteData))
    
    def _setSpaceRuleset(self, nodeRef, rulesetDef):
        """Set up rules on a space"""
        return self.doJSONPost('proxy/alfresco/api/node/%s/ruleset/rules' % (nodeRef.replace('://', '/')), json.dumps(rulesetDef))
    
    def _deleteSpaceRuleset(self, nodeRef, rulesetId):
        """Set up rules on a space"""
        return self.doJSONPost('proxy/alfresco/api/node/%s/ruleset/rules/%s' % (nodeRef.replace('://', '/'), rulesetId), method="DELETE")
    
    def importSiteContent(self, siteId, containerId, f, delete=True):
        """Upload a content package into a collaboration site and extract it"""
        # Get the site metadata
        folderType = 'cm_folder'
        siteData = self.doJSONGet('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteId))))
        siteNodeRef = '/'.join(siteData['node'].split('/')[5:]).replace('/', '://', 1)
        treeData = self.doJSONGet('proxy/alfresco/slingshot/doclib/treenode/node/%s' % (siteNodeRef.replace('://', '/')))
        # Locate the container item
        containerData = None
        tempContainerData = None
        tempContainerName = '%s-temp' % (containerId)
        for child in treeData['items']:
            if child['name'].lower() == containerId.lower():
                containerData = child
            if child['name'].lower() == tempContainerName.lower():
                tempContainerData = child
        if containerData is None:
            # Create container if it doesn't exist
            folderData = { 'alf_destination': siteNodeRef, 'prop_cm_name': containerId, 'prop_cm_title': containerId, 'prop_cm_description': '' }
            try:
                createData = self.doJSONPost('proxy/alfresco/api/type/%s/formprocessor' % (urllib.quote(unicode(folderType))), json.dumps(folderData))
            except SurfRequestError, e:
                if e.code == 404:
                    folderType = 'cm:folder'
                    createData = self.doJSONPost('proxy/alfresco/api/type/%s/formprocessor' % (urllib.quote(unicode(folderType))), json.dumps(folderData))
                else:
                    raise e
            containerData = { 'nodeRef': createData['persistedObject'], 'name' : containerId }
            # Add the tagscope aspect to the container - otherwise an error occurs when viewed by a site consumer
            resp = self.doPost('proxy/alfresco/slingshot/doclib/action/aspects/node/%s' % (str(containerData['nodeRef']).replace('://', '/')), '{"added":["cm:tagscope"],"removed":[]}', 'application/json;charset=UTF-8')
            resp.close()
            #print createData
            #raise Exception("Container '%s' does not exist" % (containerId))
        if tempContainerData is None:
            # Create upload container if it doesn't exist
            folderData = { 'alf_destination': siteNodeRef, 'prop_cm_name': tempContainerName, 'prop_cm_title': tempContainerName, 'prop_cm_description': '' }
            try:
                createData = self.doJSONPost('proxy/alfresco/api/type/%s/formprocessor' % (urllib.quote(unicode(folderType))), json.dumps(folderData))
            except SurfRequestError, e:
                if e.code == 404:
                    folderType = 'cm:folder'
                    createData = self.doJSONPost('proxy/alfresco/api/type/%s/formprocessor' % (urllib.quote(unicode(folderType))), json.dumps(folderData))
                else:
                    raise e
            tempContainerData = { 'nodeRef': createData['persistedObject'], 'name' : tempContainerName }
            
        # First apply a ruleset to the temp folder
        # This will perform the import automatically when we upload the ACP file
        rulesetDef = {
            'id': '',
            'action': {
                "actionDefinitionName":"composite-action",
                "conditions": [
                    {
                        "conditionDefinitionName":"compare-property-value",
                        "parameterValues": {
                            "operation":"ENDS",
                            "value":"-%s.acp" % (containerId),
                            "property":"cm:name"
                        }
                    }
                ],
                "actions": [
                    {
                        "actionDefinitionName":"import",
                        "parameterValues": {
                            "destination":containerData['nodeRef']
                        }
                    }
                ]
            },
            "title":"Import ACP file",
            "description":"",
            "disabled": False,
            "applyToChildren": False,
            "executeAsynchronously": False,
            "ruleType":["update"]
        }
        rulesData = self._setSpaceRuleset(tempContainerData['nodeRef'], rulesetDef)
        
        # Now upload the file
        if f is not None:
            uparams = { 'filedata' : f, 'siteid':siteId, 'containerid':tempContainerName, 'destination':'', 'username':'', 'updateNodeRef':'', 'uploadDirectory':'/', 'overwrite':'false', 'thumbnails':'', 'successCallback':'', 'successScope':'', 'failureCallback':'', 'failureScope':'', 'contentType':'cm:content', 'majorVersion':'false', 'description':'' }
            fr = self.doMultipartUpload("proxy/alfresco/api/upload", uparams)
            udata = json.loads(fr.read())
            if ('success' in udata and udata['success'] == true) or ('status' in udata and udata['status']['code'] == 200):
                nodeRef = udata['nodeRef']
                # Try to set the mimetype - required by 4.0a, which incorrectly guesses type as application/zip
                try:
                    self.updateProperties(nodeRef, {'prop_mimetype': 'application/acp', 'prop_cm_title': f.name})
                except SurfRequestError, e:
                    # Assume mimetype was not found, probably pre-4.0 instance
                    # Instead, we just need to update another property to get the ruleset to fire
                    self.updateProperties(nodeRef, {'prop_cm_title': f.name})
                    
                if delete == True:
                    # Remove the rule definition
                    self._deleteSpaceRuleset(tempContainerData['nodeRef'], rulesData['data']['id'])
                    # Delete the ACP file
                    self.deleteFile(nodeRef)
                    # Delete the temp upload container
                    self.deleteFolder(tempContainerData['nodeRef'])
            else:
                raise Exception("Could not upload file (got response %s)" % (json.dumps(udata)))
    
    def importSiteTags(self, siteId, nodeInfo):
        """Import tags into a site component"""
        tagInfo = {}
        persistedNodes = []
        
        """Retrieve a list of all the existing tags in the system
        Items will be something like
        {
            "type": "cm:category",
            "isContainer": false,
            "name": "alfresco",
            "title": "",
            "description": "",
            "modified": "2011-03-09T20:13:12.478Z",
            "modifier": "admin",
            "displayPath": "/categories/Tags",
            "nodeRef": "workspace://SpacesStore/954968a8-6d9e-41cc-a3ab-b1edfe91ea44",
            "selectable": true
        
        },"""
        tagData = self.doJSONGet('proxy/alfresco/api/forms/picker/category/alfresco/category/root/children?selectableType=cm:category&size=1000&aspect=cm:taggable')
        tagItems = tagData['data']['items']
        for item in tagItems:
            # Cache the noderefs of tags
            tagInfo[item['name']] = { 'nodeRef': item['nodeRef'] }
        for node in nodeInfo:
            docResult = None
            try:
                docResult = self._getNodeInfoByPath(siteId, node['container'], "%s/%s".replace('//', '/') % (node['path'] or '', node['name']))
            except SurfRequestError, e:
                raise
            except Exception, e:
                ename, edesc = e
                if ename == 'file_not_found':
                    print edesc
                else:
                    raise
            if docResult is not None:
                docNodeRef = docResult['node']['nodeRef'] if 'node' in docResult else docResult['metadata']['parent']['nodeRef']
                tagNodeRefs = []
                for tagName in node['tags']:
                    if tagName not in tagInfo:
                        # Add to repo via post, cache nodeRef
                        tagResp = self.doJSONPost('proxy/alfresco/api/tag/workspace/SpacesStore', {'name': tagName})
                        tagInfo[tagName] = { 'nodeRef': tagResp['nodeRef'] }
                    tagNodeRefs.append(tagInfo[tagName]['nodeRef'])
                # Add tags to document
                try:
                    formResult = self.updateProperties(docNodeRef, {'prop_cm_taggable': ','.join(tagNodeRefs)})
                    persistedNodes.append(formResult['persistedObject'])
                except SurfRequestError, e:
                    if e.code == 500:
                        print 'Failed to save tags %s for node %s' % (','.join(tagNodeRefs), docNodeRef)
                        print e
                        e.printCallStack()
                    else:
                        raise
            
        return persistedNodes
    
    def deleteFile(self, f):
        return self.doJSONPost('proxy/alfresco/slingshot/doclib/action/file/node/%s' % (f.replace('://', '/')), method="DELETE")
    
    def deleteFolder(self, f):
        return self.doJSONPost('proxy/alfresco/slingshot/doclib/action/folder/node/%s' % (f.replace('://', '/')), method="DELETE")
    
    def updateProperties(self, nodeRef, properties):
        """Update the metadata properties of a repository item"""
        return self.doJSONPost('proxy/alfresco/api/node/%s/formprocessor' % (urllib.quote(unicode(nodeRef).replace('://', '/'))), properties)
    
    def addUserGroups(self, user, groups):
        if isinstance(user, (dict)):
            userData = user
        elif isinstance(user, (str, unicode)):
            userData = self.doJSONGet('proxy/alfresco/api/people/%s?groups=true' % (urllib.quote(unicode(user))))
        else:
            raise Exception('Bad user data type %s' % (type(user)))
        
        userGroups = []
        addGroups = []
        # Get the groups the user is a member of - since we can't add users to a group twice
        for group in userData['groups']:
            userGroups.append(group['itemName'])
        for group in groups:
            if isinstance(group, (dict)):
                if 'fullName' in group:
                    groupName = group['fullName']
                elif 'itemName' in group:
                    groupName = group['itemName']
                else:
                    raise Exception('Could not locate group name')
            elif isinstance(user, (str)):
                groupName = group
            else:
                raise Exception('Bad group type %s' % (type(group)))
            
            if groupName not in userGroups:
                addGroups.append(groupName)
        
        putData = { 'addGroups': addGroups, 'disableAccount': False, 'email': userData['email'], 'firstName': userData['firstName'], 'lastName': userData['lastName'], 'quota': userData['quota'], 'removeGroups': [] }
        return self.doJSONPost('proxy/alfresco/api/people/%s' % (urllib.quote(unicode(userData['userName']))), json.dumps(putData), method="PUT")
    
    def importRmSiteContent(self, siteId, containerId, f):
        """Upload a content package into an RM site and extract it"""
        # Forces creation of the doclib container
        resp = self.doGet('page/site/%s/documentlibrary' % (siteId))
        resp.close()

        # We need to add the user to the Records Management Administrator group(s) before we can add the content
        # Find the Records Management Administrator groups(s)
        raGroups = self.doJSONGet('proxy/alfresco/api/groups?zone=APP.DEFAULT&shortNameFilter=**Records%20Management%20Administrator')['data']
        self.addUserGroups(self._username, raGroups)
        
        # Get the site metadata
        siteData = self.doJSONGet('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteId))))
        siteNodeRef = '/'.join(siteData['node'].split('/')[5:]).replace('/', '://', 1)
        treeData = self.doJSONGet('proxy/alfresco/slingshot/doclib/treenode/node/%s' % (siteNodeRef.replace('://', '/')))
        # Locate the container item
        containerData = None
        for child in treeData['items']:
            if child['name'].lower() == containerId.lower():
                containerData = child
        if containerData is None:
            # Throw an error if the container doesn't exist
            raise Exception("Could not find the RM documentLibrary container and it cannot be created")
        uparams = { 'archive' : f, 'destination':containerData['nodeRef'] }
        fr = self.doMultipartUpload("proxy/alfresco/api/rma/admin/import", uparams)
        udata = json.loads(fr.read())
        if ('success' in udata and udata['success']) or ('status' in udata and udata['status']['code'] == 200):
            pass
        else:
            raise Exception("Could not upload file (got response %s)" % (json.dumps(udata)))

    def exportSiteContent(self, siteId, containerId, includePaths, tempContainerName='export', async=False):
        """Export an ACP file of a specific site component and store it in the repository"""
        # Get the site metadata
        siteData = self.doJSONGet('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteId))))
        siteNodeRef = '/'.join(siteData['node'].split('/')[5:]).replace('node/', '').replace('/', '://', 1)
        treeData = self.doJSONGet('proxy/alfresco/slingshot/doclib/treenode/node/%s' % (siteNodeRef.replace('://', '/')))
        acpFile = "%s-%s" % (siteId, containerId)
        # Locate the container item
        containerData = None
        tempContainerData = None
        for child in treeData['items']:
            if child['name'].lower() == containerId.lower():
                containerData = child
            if child['name'].lower() == tempContainerName.lower():
                tempContainerData = child
        if containerData is None:
            raise Exception("Container '%s' does not exist" % (containerId))
            
        if tempContainerData is None:
            # Create export container if it doesn't exist
            folderData = { 'alf_destination': siteNodeRef, 'prop_cm_name': tempContainerName, 'prop_cm_title': tempContainerName, 'prop_cm_description': '' }
            try:
                createData = self.doJSONPost('proxy/alfresco/api/type/cm_folder/formprocessor', json.dumps(folderData))
            except SurfRequestError, e:
                if e.code == 404:
                    # 4.0 syntax
                    createData = self.doJSONPost('proxy/alfresco/api/type/%s/formprocessor' % (urllib.quote('cm:folder')), json.dumps(folderData))
                else:
                    raise e
            tempContainerData = { 'nodeRef': createData['persistedObject'], 'name' : tempContainerName }
        else:
            # Does the ACP file exist in the export container already?
            docList = self._getDocumentList('%s/%s/%s' % (self.getSitesContainerName(), siteId, tempContainerName))
            acp = self._getDocumentListItem(docList, '%s.acp' % (acpFile))
            if acp is not None:
                self.deleteFile(acp['nodeRef'])
        
        # Execute the export action and run it directly
        actionDef = {
            "actionedUponNode":containerData['nodeRef'],
            "actionDefinitionName":"export",
            "parameterValues": {
                "package-name": acpFile,
                "destination": tempContainerData['nodeRef'],
                "include-children": True,
                "include-self": False,
                "store": "workspace://SpacesStore",
                "encoding": "UTF-8"
            }
        }
        if (includePaths is not None and includePaths != ""):
            # Add cm: prefix to path parts, if no prefix present
            paths = ["/".join([ (part if part.find(":") > 0 else ("cm:%s" % (part))) for part in p.split("/") ]) for p in includePaths]
            fullpaths = []
            for p in paths:
                fullpaths.append(p if p.startswith("/app:company_home") else "/app:company_home/st:sites/cm:%s/%s" % (siteId, p.strip("/")))
            actionDef["parameterValues"]["include-paths"] = fullpaths
        self.doJSONPost('proxy/alfresco/api/actionQueue?async=%s' % (str(async).lower()), json.dumps(actionDef))
        """
        Response is something like
        {
            "data" : 
            {
                "status" : "success",
                "actionedUponNode" : "workspace://SpacesStore/2e78a675-0f48-4e3d-b03f-0ae724eb5f9f",
                "action" : 
                {"actionDefinitionName": ... }
            }
        }
        """
        
    def exportAllSiteContent(self, siteId, containers=None, includePaths=None, tempContainerName='export', async=False):
        """Export an ACP file for each component in the site and store them in the repository"""
        # TODO Can we not just call proxy/alfresco/slingshot/doclib/treenode/node/alfresco/company/home/Sites/sitename ?
        siteData = self.doJSONGet('proxy/alfresco/api/sites/%s' % (urllib.quote(unicode(siteId))))
        siteNodeRef = '/'.join(siteData['node'].split('/')[5:]).replace('node/', '').replace('/', '://', 1)
        treeData = self.doJSONGet('proxy/alfresco/slingshot/doclib/treenode/node/%s' % (siteNodeRef.replace('://', '/')))
        results = { 'exportFiles': [] }
        excludeContainers = ['export', 'surf-config', 'temp']
        # Locate the container item
        for child in treeData['items']:
            if (containers is None or child['name'] in containers) and (child['name'] not in excludeContainers) and not child['name'].startswith('export-'):
                # treenode webscript does not return any discussion items, need to use posts web script instead
                if child['name'] != 'discussions':
                    docList = self._getDocumentList('%s/%s/%s' % (self.getSitesContainerName(), siteId, child['name']))
                    totalRecords = docList['totalRecords']
                else:
                    postList = self.doJSONGet('service/components/forum/site/%s/discussions/posts?contentLength=8&page=1&pageSize=10&startIndex=0' % (siteId))
                    totalRecords = postList['total']

                if totalRecords > 0:
                    print "Export %s" % (child['name'])
                    self.exportSiteContent(siteId, child['name'], includePaths, tempContainerName, async)
                    results['exportFiles'].append(child['name'])
        return results
    
    def _getNodeInfoByPath(self, siteId, componentId, path):
        """Return information on the specified node"""
        try:
            parentPath = path[0:path.rindex('/')]
            dl2resp = self.doJSONGet('proxy/alfresco/slingshot/doclib2/doclist/space/site/%s/%s/%s' % (urllib2.quote(siteId), urllib2.quote(componentId), urllib2.quote(parentPath.encode('utf-8'))))
            for item in dl2resp['items']:
                if str(item['node']['properties']['cm:name']) == str(path[path.rindex('/') + 1:]):
                    return item
            raise Exception('file_not_found', 'Could not find file %s in component %s, parent folder %s' % (path[path.rindex('/') + 1:], componentId, parentPath))
        except SurfRequestError, e:
            if e.code == 404: # Pre-4.0 method
                return self.doJSONGet('proxy/alfresco/slingshot/doclib/doclist/all/node/alfresco/company/home/%s/%s/%s/%s' % (urllib2.quote(self.getSitesContainerName()), urllib2.quote(siteId), urllib2.quote(componentId), urllib2.quote(path.encode('utf-8'))))
            else:
                raise
    
    def _getDocumentList(self, space):
        """Return a list of documents in the space identified by parameter space
        
        Response will be something like
        {
           "totalRecords": 9,
           "startIndex": 0,
           "metadata":
           {
              "parent":
              {
                 "nodeRef": "workspace://SpacesStore/e9bc6bf6-d399-497f-b6d2-c31afbe1a2b0",
                 "permissions":
                 {
                    "userAccess":
                    {
                       "permissions": true,
                       "edit": true,
                       "delete": true,
                       "cancel-checkout": false,
                       "create": true
                    }
                 }
              },
              "onlineEditing": true,
              "itemCounts":
              {
                 "folders": 9,
                 "documents": 0
              }
           },
           "items":
           [
              {
                   "nodeRef": "workspace://SpacesStore/c11231d1-31f4-4b5e-8425-e4c7234827e2",
                   "nodeType": "cm:folder",
                   "type": "folder",
                   "mimetype": "",
                   "isFolder": true,
                   "isLink": false,
                   "fileName": "Content for Partner Site",
                   "displayName": "Content for Partner Site",
                   "status": "",
                   "title": "",
                   "description": "Put your content here. Not for project management type doc's",
                   "author": "",
                   "createdOn": "08 Apr 2010 19:44:58 GMT+0100 (BST)",
                   "createdBy": "Paul Jongen",
                   "createdByUser": "pjongen",
                   "modifiedOn": "01 Jun 2010 16:00:40 GMT+0100 (BST)",
                   "modifiedBy": "Paul Jongen",
                   "modifiedByUser": "pjongen",
                   "lockedBy": "",
                   "lockedByUser": "",
                   "size": "0",
                   "version": "1.0",
                   "contentUrl": "api/node/content/workspace/SpacesStore/c11231d1-31f4-4b5e-8425-e4c7234827e2/Content%20for%20Partner%20Site",
                   "webdavUrl": "\/webdav\/Sites\/PEP\/documentLibrary\/Content%20for%20Partner%20Site",
                   "actionSet": "folder",
                   "tags": [],
                   "categories": [],
                   "activeWorkflows": "",
                   "isFavourite": false,
                   "location":
                   {
                      "site": "",
                      "siteTitle": "",
                      "container": "",
                      "path": "\/Sites\/PEP\/documentLibrary",
                      "file": "Content for Partner Site"
                   },
                   "permissions":
                   {
                      "inherited": true,
                      "roles":
                      [
                         "ALLOWED;GROUP_site_PEP_SiteManager;SiteManager;INHERITED",
                         "ALLOWED;GROUP_EVERYONE;SiteConsumer;INHERITED",
                         "ALLOWED;GROUP_EVERYONE;ReadPermissions;INHERITED",
                         "ALLOWED;GROUP_site_PEP_SiteContributor;SiteContributor;INHERITED",
                         "ALLOWED;GROUP_site_PEP_SiteConsumer;SiteConsumer;INHERITED",
                         "ALLOWED;GROUP_site_PEP_SiteCollaborator;SiteCollaborator;INHERITED"
                      ],
                      "userAccess":
                      {
                         "permissions": true,
                         "edit": true,
                         "delete": true,
                         "cancel-checkout": false,
                         "create": true
                      }
                   }
           ]
        }
        """
        
        # Assume space is a path for now e.g. 'Sites/test/documentLibrary'
        return self.doJSONGet('proxy/alfresco/slingshot/doclib/doclist/all/node/alfresco/company/home/%s' % (urllib.quote(unicode(space))))
    
    def _getDocumentListItem(self, list, itemName):
        for item in list['items']:
            if item['fileName'] == itemName:
                return item
        return None
    
    def _documentListHasItem(self, list, itemName):
        return self._getDocumentListItem(list, itemName) is not None

    def updateContentItem(self, nodeRef, content, majorVersion=False, description=''):
        return self.doMultipartUpload("proxy/alfresco/api/upload", {
            'filedata': content, 
            'siteid': '', 
            'containerid': '', 
            'destination': '',
            'username': '', 
            'updateNodeRef': nodeRef, 
            'uploadDirectory':'', 
            'overwrite': 'false', 
            'thumbnails': '',
            'successCallback': '',
            'successScope': '',
            'failureCallback': '',
            'failureScope': '',
            'contentType': 'cm:content',
            'majorVersion': str(majorVersion).lower(),
            'description': description
        })
    
    # Admin functions
    
    def getAllUsers(self, getFullDetails=False, getDashboardConfig=False, getPreferences=False, getGroups=False):
        """Fetch information on all the person objects in the repository
        
        getFullDetails adds 'capabilities' object to the user object with booleans
        isMutable, isGuest and isAdmin
        
        getGroups adds 'groups' and 'mutability' objects. Implies getFullDetails=True.
        """
        pdata = self.doJSONGet('proxy/alfresco/api/people')
        self._extendUserInfo(pdata['people'], getFullDetails, getDashboardConfig, getPreferences, getGroups)
        return pdata
        
    def getCloudUsers(self, getFullDetails=False, getDashboardConfig=False, getPreferences=False, getGroups=False):
        """Fetch information on all the person objects in the current tenant
        
        getFullDetails adds 'capabilities' object to the user object with booleans
        isMutable, isGuest and isAdmin
        
        getGroups adds 'groups' and 'mutability' objects. Implies getFullDetails=True.
        """
        pdata = { 'people': [] }
        skipCount = 0
        pageSize = 100
        while True:
            newData = self.doJSONGet('proxy/alfresco/internal/cloud/people?sortBy=userName&skipCount=%s&maxItems=%s' % (skipCount, pageSize))
            self._extendUserInfo(newData['data'], getFullDetails, getDashboardConfig, getPreferences, getGroups)
            pdata['people'].extend(newData['data'])
            skipCount += pageSize
            if skipCount >= newData['paging']['totalItems']:
                break
        return pdata
        
    def _extendUserInfo(self, users, getFullDetails=False, getDashboardConfig=False, getPreferences=False, getGroups=False):
        """Fetch information on all the person objects in the repository
        
        getFullDetails adds 'capabilities' object to the user object with booleans
        isMutable, isGuest and isAdmin
        
        getGroups adds 'groups' and 'mutability' objects. Implies getFullDetails=True.
        """
        if getFullDetails or getDashboardConfig or getPreferences:
            for p in users:
                if getGroups:
                    p.update(self.doJSONGet('proxy/alfresco/api/people/%s?groups=true' % (urllib.quote(unicode(p['userName'])))))
                    # Remove site groups and those with a GUID in them (e.g. RM security groups)
                    groups = []
                    for g in p['groups']:
                        if not g['itemName'].startswith('GROUP_site_') and GUID_REGEXP.search(g['itemName']) is None:
                            groups.append(g)
                    p['groups'] = groups
                elif getFullDetails:
                    p.update(self.doJSONGet('proxy/alfresco/api/people/%s' % (urllib.quote(unicode(p['userName'])))))
                if getDashboardConfig:
                    dc = self.getDashboardConfig('user', p['userName'])
                    if dc != None:
                        p['dashboardConfig'] = dc
                if getPreferences:
                    p['preferences'] = self.doJSONGet('proxy/alfresco/api/people/%s/preferences' % (urllib.quote(unicode(p['userName']))))
        
    def createUser(self, user, defaultPassword=None):
        """Create a person object in the repository"""
        # Work around bug where create/update user calls do not accept null values
        # Create call does not like jobtitle being null; webtier update profile does not tolerate any being null
        for k in user.keys():
            if user[k] is None:
                user[k] = ""
        if not ('password' in user):
            print "Warning: using default password for user %s" % (user['userName'])
            if defaultPassword is not None and defaultPassword != '':
                user['password'] = defaultPassword
            else:
                user['password'] = user['userName']
        return self.doJSONPost('proxy/alfresco/api/people', json.dumps(user))

    def createUsers(self, users, skip_users=[], default_password=None):
        """Create several person objects in the repository"""
        for u in users:
            if not (u['userName'] in skip_users):
                print "Creating user '%s'" % (u['userName'])
                try:
                    self.createUser(u, default_password)
                except urllib2.HTTPError, e:
                    if e.code == 409:
                        print "User '%s' already exists, skipping" % (u['userName'])
                    else:
                        print e
                # Add user groups if they exist
                if 'groups' in u and len(u['groups']) > 0:
                    self.addUserGroups(u['userName'], u['groups'])
    
    def setUserPreferences(self, username, prefs):
        return self.doJSONPost('proxy/alfresco/api/people/%s/preferences' % (urllib.quote(unicode(username))), json.dumps(prefs))
    
    def deleteUser(self, user):
        """Delete an existing user from Share"""
        return self.doJSONPost("%s/%s" % ('proxy/alfresco/api/people', urllib.quote(unicode(user))), data="", method="DELETE")

    def deleteUsers(self, users):
        """Delete several person objects from the repository"""
        for u in users:
            print "Deleting user '%s'" % (u['userName'])
            try:
                self.deleteUser(u['userName'])
            except SurfRequestError, e:
                if e.code == 404:
                    print "User '%s' did not exist, skipping" % (u['userName'])
                else:
                    raise e
    
    def getAllGroups(self, skipGroups=[], getSiteGroups=False, getSystemGeneratedGroups=False, zone='APP.DEFAULT'):
        """Fetch information on all the group objects in the repository"""
        gdata = self.doJSONGet('proxy/alfresco/api/rootgroups?zone=%s' % (urllib.quote(zone)))
        groups = []
        for g in gdata['data']:
            if g['shortName'] not in skipGroups:
                # Site groups
                if g['shortName'].startswith('site_'):
                    if getSiteGroups:
                        groups.append(g)
                elif GUID_REGEXP.search(g['shortName']) is not None:
                    if getSystemGeneratedGroups:
                        groups.append(g)
                else:
                    groups.append(g)
        for g in groups:
            g['children'] = self.doJSONGet('proxy/alfresco/api/groups/%s/children' % (urllib.quote(unicode(g['shortName']))))['data']
        return { 'groups': groups }
    
    def getGroup(self, name):
        """Return a single group object from the repository, or None if it does not exist"""
        try:
            group = self.doJSONGet('proxy/alfresco/api/groups/%s' % (urllib.quote(unicode(name))))
            return group
        except SurfRequestError, e:
            if e.code == 404:
                return None
            else:
                raise e
    
    def createGroup(self, name, displayName, parent=None):
        """Create a single group authority"""
        if parent is None:
            self.doJSONPost('proxy/alfresco/api/rootgroups/%s' % (urllib.quote(unicode(name))), {'displayName':displayName})
        else:
            self.doJSONPost('proxy/alfresco/api/groups/%s/children/GROUP_%s' % (urllib.quote(unicode(parent)), urllib.quote(unicode(name))))
            self.doJSONPost('proxy/alfresco/api/groups/%s' % (urllib.quote(unicode(name))), {'displayName':displayName}, method='PUT')
    
    def createGroups(self, group, parent=None):
        """Create a group authority with nested sub-groups"""
        # Only create the group if it doesn't already exist
        if self.getGroup(group['shortName']) is None:
            self.createGroup(group['shortName'], group['displayName'], parent)
        if 'children' in group:
            if parent is None:
                childBase = group['displayName']
            else:
                childBase = '%s/%s' % (parent, group['displayName'])
            for child in group['children']:
                self.createGroups(child, childBase)
    
    def getCategories(self, path):
        """Fetch a list of child categories at the given location, in a recursive structure"""
        categories = self.doJSONGet('proxy/alfresco/slingshot/doclib/categorynode/node/%s' % (urllib.quote(path.encode('utf-8'))))['items']
        # Recursively call the function on each child to find child categories
        for c in categories:
            c['children'] = self.getCategories('%s/%s' % (path, c['name']))
        return categories
    
    def getAllCategories(self):
        """Fetch all the categories in the repository, in a tree structure"""
        return self.getCategories('alfresco/category/root')
    
    def getAllTags(self):
        """Fetch all the tags used in the repository"""
        resp = self.doGet('proxy/alfresco/api/tags/workspace/SpacesStore')
        tags = resp.read().strip("[] \r\n\t").replace("\r", '').replace("\n", '').replace("\t", '').split(',')
        resp.close()
        # Remove empty tags
        while '' in tags:
            tags.remove('')
        tags.sort()
        return tags

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '-version', '--version'):
        print SIE_VERSION
