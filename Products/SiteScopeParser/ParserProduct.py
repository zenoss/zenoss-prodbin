#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

"""ParserProduct

An implementation of the ParserProductInt interface.

$Id: ParserProduct.py,v 1.31 2002/11/08 18:03:40 edahl Exp $"""

__version__ = "$Revision: 1.31 $"[11:-2]

from Products.ZenUtils.ObjectCache import ObjectCache
from ParserProductInt import ParserProductInt
from SiteScopeParser import SiteScopeParser, SiteScopeFirstParser
from SiteScopeRow import SiteScopeRow
from SiteScopeExcept import *

import urllib2
import time
import pprint
import base64
import re
import zLOG

from Acquisition import Implicit
from Globals import Persistent
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl.Role import RoleManager
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from OFS.SimpleItem import Item
#from OFS.PropertyManager import PropertyManager
from App.Dialogs import MessageDialog

manage_addParserForm = DTMLFile('dtml/addParserForm',globals())


def manage_addParser(context, id, title='', url='localhost',
                    user='', password='', first=0, 
                    timeout=60, REQUEST=None):

    "Add a SiteScopeParser instance to a container" 
    try:
        p = ParserProduct(id, title, url, user, password, first, timeout)
    except UrlFormatError, error:
        return error.dialog()
    context._setObject(id, p)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class ParserProduct(Implicit,Persistent,RoleManager,Item,ObjectCache):
    "Product to manage the results of parsing SiteScope's output"

    __implements__ = ParserProductInt #name of implemented interface
    meta_type = "SiteScopeParser"   #name in management interface

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    manage_editParserForm = DTMLFile('dtml/manageEditParserForm',globals())

    
    manage_options = (
        ({  'label':    'Edit',
            'action':   'manage_editParserForm',
            'help':     ('SiteScopeParser','SiteScopeParser_Edit.stx'),
            'target':   'manage_main'},
        {   'label':    'View',
            'action':   'displayTable',
            'help':     ('SiteScopeParser','SiteScopeParser_Add.stx'),
            'target':   'manage_main'},)
        +ObjectCache.manage_options
        +RoleManager.manage_options
        +Item.manage_options)


    def __init__(self,id,title,url,user,
                    password,first=0,timeout=60):
        ''' Construct product instance

        Note: _parsedData is not initialized (and therefor
        the URL is not checked) on instantiation because
        we couldn't alert the user without the capability
        to return a value'''

        # kill first and re.match the url
        # to see if it's got SiteScope.html in it...
        self.id = id
        self.title = title
        self.url = url
        self.user = user
        self.password = password
        self.first = first
        self.timeout = timeout
        ObjectCache.__init__(self)
        self.initCache()
        (self._baseHref, self._host) = self._setURLbases(self.url)
      

    def _setURLbases(self,url):
        '''Matches the host and base url of the sitescope server'''
        # FIXME: need to handle error conndtion better here if regex fails
        retval = []
        matchobj = re.search(r'(?:/+)([^/]+)(/(?:[^/]+/)+)',url)
        if not matchobj:
            raise UrlFormatError("You must specify the protocol:// "+
                "parameter of the URL")
        retval.append(matchobj.group(1) + matchobj.group(2))
        retval.append(matchobj.group(1))
        return retval


    def _createParser(self, url):
        '''Creates the appropriate kind of parser based on
        whether or not the target is the first page in
        SiteScope'''
        p = None
        if url.find("SiteScope.html") > 0:
            p = SiteScopeFirstParser(self.REQUEST)
        else:
            p = SiteScopeParser(self.REQUEST)
        return p


    def _loadParseTree(self, url):
        "Loads a file over the web and parses it, setting the parse time"

        htmlsrc = None
        try:
            request=urllib2.Request(url)
            if self.user and self.password:
                request.add_header('Authorization',
                    'Basic '+base64.encodestring(
                        urllib2.unquote("%s:%s" % (self.user,
                            self.password))).strip())
            socket = urllib2.urlopen(request)
            htmlsrc = socket.read()
            socket.close()
        except urllib2.HTTPError,error:
            if error.code == 404:
                raise LocationError(url)
            elif error.code == 401:
                raise AuthError(self.user)
        except urllib2.URLError:
            raise HostError(self._host)
        # CV returns login screen for 404s
        if htmlsrc.lower().find("_password")>0:
            raise LocationError(url)
        p = self._createParser(url)
        p.feed(htmlsrc)
        try:
            retval = p.getResults()
            retval.fixRows(self._host, self._baseHref)
        except:
            raise ParseError(url)
        return retval


    """def _needsReload(self,url):
        "Checks to see if the parse tree needs to be reloaded"

        retval = 0
        if (not self.checkCache(url) or 
            (time.time() - self.checkCache(url).getTimeStamp()) >= self.timeout):
            
            retval = 1
        return retval
    """


    def _getParseTree(self,url=None):
        '''Checks to see that the parse tree is available,
        gets it if it isn't, and returns the tree'''

        if not url: url = self.url
        retval = self.checkCache(url)
        if not retval:
            retval = self._loadParseTree(url)
            self.addToCache(url, retval)
        return retval


    security.declarePublic("Get row from name",'getRowByName')
    def getRowByName(self,name,refUrl=None):
        "Returns a single row corresponding to the passed in name"

        if refUrl:
            url = refUrl
        else:
            form = self.REQUEST.form
            if form.has_key('refUrl'):
                url = form['refUrl'][1:-1]
            else:
                url = None 
        pd = self._getParseTree(url)

        for row in pd.getRows():
            if row.isNamed(name):
                return row


    security.declarePublic('Get list of all rows','getTableList')
    def getRowList(self, refUrl=None):
        "Returns all rows in the format of a list"

        
        if refUrl:
            url = refUrl
        else:
            form = self.REQUEST.form
            if form.has_key('refUrl'):
                url = form['refUrl'][1:-1]
            else:
                url = None 
        return self._getParseTree(url).getRows()


    security.declarePublic('Get HTML version of the table','index_html')
    def displayTable(self,url=None,refUrl=None):
        "Default display"
       
        if refUrl: 
            url = refUrl[1:-1]
        elif not url:   
            url = self.url
        insttree = self._getParseTree(url)

        retval = ''
        cols = insttree.getCols()

        retval += '<html><head><title>%s' % self.title
        retval += '</title></head><body><table border="1"><tr>\n'
        for item in cols.keys():
            retval += "<th>%s</th>" % item
        retval += "</tr>\n"
        for row in insttree.getRows():
            retval += "<tr>"
            cols = row.columns()
            for key in cols.keys():
                retval += "<td>"
                if key == 'Condition':
                    retval += row.ConditionImg()
                elif key == 'Name':
                    retval += "<a href=" + row.NameAutoUrl() + ">"
                    retval += row.Name() + "</a>" 
                else:    
                    retval += cols[key]()
                retval += "</td>"
            retval += "</tr>\n"
        retval += "</table></body></html>"
        return retval

    security.declareProtected("Change Parser Object", "manage_editParser")
    def manage_editParser(self,title,url,user,password,
                            first=0,timeout=30,REQUEST=None):
        '''Change objects member data and try the new URL,
        raising an error if it fails'''

        self.title = title
        self.url = url
        self.user = user
        self.password = password
        self.first = first
        self.timeout = timeout
        try:
            (self._baseHref, self._host) = self._setURLbases(self.url)

            self.cleanCache()
            self.addToCache(self.url, self._getParseTree())
        except CMException, error:
            return error.dialog()

        if REQUEST:
            message = "Saved Changes"
            return self.manage_editParserForm(self, REQUEST,
                                                manage_tabs_message=message)


    security.declareProtected("Change Parser Object", "manage_clearCache")
    def manage_clearCache(self, REQUEST=None):
        """manual clear of cache"""
        self.cleanCache()
        if REQUEST:
            message = "Cleared Cache."
            return self.editCache(self,REQUEST,manage_tabs_message=message)
                                                
    security.declareProtected("Change Parser Object", "manage_editCache")
    def manage_editCache(self, timeout=20, clearthresh=20, REQUEST=None):
        """set cache values"""
        self.timeout = int(timeout)
        self.clearthresh = int(clearthresh)
        if REQUEST:
            message = "Saved Changes."
            return self.editCache(self,REQUEST,manage_tabs_message=message)
        


InitializeClass(ParserProduct)


if __name__ == "__main__":
    x=ParserProduct("http://10.2.1.154:8888/SiteScope/htdocs/SiteScope.html",1,500)
    x.index_html()
