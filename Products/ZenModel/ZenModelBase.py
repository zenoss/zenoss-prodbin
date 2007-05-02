###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ZenModelBase

$Id: ZenModelBase.py,v 1.17 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.17 $"[11:-2]

import copy
import re
import time

import sys 
from urllib import unquote
from OFS.ObjectManager import checkValidId as globalCheckValidId

from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from Globals import InitializeClass
from Acquisition import aq_base, aq_chain

from Products.CMFCore.utils import _verifyActionPermissions

from Products.ZenUtils.Utils import zenpathsplit, zenpathjoin
from Products.ZenUtils.Utils import createHierarchyObj, getHierarchyObj
from Products.ZenUtils.Utils import getObjByPath

from Products.ZenUtils.Utils import prepId as globalPrepId

# Custom device properties start with c
iscustprop = re.compile("^c[A-Z]").search

class ZenModelBase(object):
    """
    All ZenModel Persistent classes inherit from this class.  It provides
    some screen management functionality, and general utility methods.
    """
    sub_meta_types = ()
    #prodStateThreshold = 500

    security = ClassSecurityInfo()

    def __call__(self):
        """
        Invokes the default view.
        """
        view = "view"
        if hasattr(self, "factory_type_information"):
            view = self.factory_type_information[0]['immediate_view']
        else:
            raise 'Not Found', ('Cannot find default view for "%s"' %
                                '/'.join(self.getPhysicalPath()))
        return self.restrictedTraverse(view)()

    index_html = None  # This special value informs ZPublisher to use __call__


    security.declareProtected('View', 'view')
    def view(self):
        '''
        Returns the default view even if index_html is overridden.
        '''
        return self()

    
    def __hash__(self):
        return hash(self.id)

    def prepId(self, id, subchar='_'):
        return globalPrepId(id, subchar)

    def checkValidId(self, id):
        """Checks a valid id
        """
        new_id = unquote(id)
        new_id = new_id.replace('/', '_')
        try: 
            globalCheckValidId(self, new_id)
            try:
                globalCheckValidId(self, self.prepId(id=new_id))
                return True
            except:
                return str(sys.exc_info()[1])
        except:
            return str(sys.exc_info()[1])
        
    def getIdLink(self):
        """Return an A link to this object with its id as the name.
        """
        return "<a href='%s'>%s</a>" % (self.getPrimaryUrlPath(), self.id)


    def callZenScreen(self, REQUEST, redirect=False):
        """
        Call and return screen specified by zenScreenName value of REQUEST.
        If zenScreenName is not present call the default screen.  This is used
        in functions that are called from forms to get back to the correct
        screen with the correct context.
        """
        if getattr(REQUEST, 'dontRender', False):
            # EventView uses a FakeRequest class to avoid the overhead
            # of rendering pages as result of ajax calls.
            return ''
        screenName = REQUEST.get("zenScreenName", "")
        if redirect:
            nurl = "%s/%s" % (self.getPrimaryUrlPath(), screenName)
            REQUEST['RESPONSE'].redirect(nurl)
        else:
            REQUEST['URL'] = "%s/%s" % (self.absolute_url_path(), screenName)
            screen = getattr(self, screenName, False)
            if not screen: return self()
            return screen()


    def zenScreenUrl(self):
        """
        Return the url for the current screen as defined by zenScreenName.
        If zenScreenName is not found in the request the request url is used. 
        """
        screenName = self.REQUEST.get("zenScreenName", "")
        if not screenName: return self.REQUEST.URL
        return self.getPrimaryUrlPath() + "/" + screenName


    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object.
        [('url','id'), ...]
        """
        links = []
        curDir = self.primaryAq()
        while curDir.id != terminator:
            if curDir.meta_type == 'ToManyContRelationship':
                curDir = curDir.getPrimaryParent()
                continue
            if not getattr(aq_base(curDir),"getPrimaryUrlPath", False):
                break
            links.append(
                (curDir.getPrimaryUrlPath(),
                curDir.id))
            curDir = curDir.aq_parent
        links.reverse()
        return links
    
    
    security.declareProtected('View', 'zentinelTabs')
    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = []
        user = getSecurityManager().getUser()
        actions = self.factory_type_information[0]['actions']
        for a in actions:
            def permfilter(p): return user.has_permission(p,self)
            permok = filter(permfilter, a['permissions'])
            if not a.get('visible', True) or not permok:
                continue
            a = a.copy()
            if a['action'] == templateName: a['selected'] = True
            tabs.append(a)
        return tabs


    security.declareProtected('Manage DMD', 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        """Edit a ZenModel object and return its proper page template
        """
        self.manage_changeProperties(**REQUEST.form)
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
            return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'getPrimaryDmdId')
    def getPrimaryDmdId(self, rootName="dmd", subrel=""):
        """get the full dmd id of this object strip off everything before dmd"""
        path = list(self.getPrimaryPath())
        path = path[path.index(rootName)+1:]
        if subrel: path = filter(lambda x: x != subrel, path)
        return '/'+'/'.join(path)
  

    def zenpathjoin(self, path):
        return zenpathjoin(path)


    def zenpathsplit(self, path):
        return zenpathsplit(path)


    def createHierarchyObj(self, root, name, factory, relpath="", log=None):
        return createHierarchyObj(root, name, factory, relpath, log)


    def getHierarchyObj(self, root, name, relpath):
        return getHierarchyObj(root, name, relpath)


    def getDmd(self):
        """return the dmd root object"""
        for obj in aq_chain(self):
            if obj.id == 'dmd': return obj
            

    def getDmdRoot(self, name):
        """return an organizer object by its name"""
        dmd = self.getDmd()
        return dmd._getOb(name)

    
    def getDmdObj(self, path):
        """get object from path that starts at dmd ie. /Devices/Servers/box"""
        if path.startswith("/"): path = path[1:]
        return self.getDmd().getObjByPath(path)
   

    def getZopeObj(self, path):
        "get object from path tat starts at zope root ie. /zport/dmd/Devices"
        return self.getObjByPath(path)


    def getNowString(self):
        """return the current time as a string"""
        return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())


    def todayDate(self):
        """Return today's date as a string in the format 'mm/dd/yyyy'."""
        return time.strftime("%m/%d/%Y", time.localtime())


    def yesterdayDate(self):
        """Return yesterday's date as a string in the format 'mm/dd/yyyy'."""
        yesterday = time.time() - 24*3600
        return time.strftime("%m/%d/%Y", time.localtime(yesterday))


    def all_meta_types(self, interfaces=None):
        """Control what types of objects can be created within classification"""
        mts = super(ZenModelBase,self).all_meta_types(interfaces)
        if self.sub_meta_types:
            mts = filter(lambda mt: mt['name'] in self.sub_meta_types, mts)
        return mts


    security.declareProtected('Delete objects', 'manage_deleteObjects')
    def manage_deleteObjects(self, ids=(), REQUEST=None):
        """Delete object by id from this object.
        """
        for id in ids:  self._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def custPropertyIds(self):
        """List custom properties that are defined at root node.
        """
        return self.zenPropertyIds(pfilt=iscustprop)
        
   
    def custPropertyMap(self):
        """List custom property definitions
        [{'id':'cName','label':'Name', 'type':'string'},]
        """
        return self.zenPropertyMap(pfilt=iscustprop)


    def visibleCustPropertyMap(self):
        """List custom property definitions that should be visible
        [{'id':'cName','label':'Name', 'type':'string'},]
        """
        return [ p for p in self.zenPropertyMap(pfilt=iscustprop) \
                    if p.get('visible', True) ]


    def saveCustProperties(self, REQUEST):
        """Save custom properties from REQUEST.form.
        """
        return self.saveZenProperties(iscustprop, REQUEST)

    def getObjByPath(self, path):
        return getObjByPath(self, path)

    def isLocalName(self, name):
        """Check to see if a name is local to our current context.
        """
        v = getattr(aq_base(self), name, '__ZENMARKER__')
        return v != '__ZENMARKER__'


    security.declareProtected('View', 'helpLink')
    def helpLink(self):
        '''return a link to the objects help file'''
        path = self.__class__.__module__.split('.')
        className = path[-1].replace('Class','')
        product = path[-2]
       
        path = ("", "Control_Panel", "Products", product, "Help",
                "%s.stx"%className)

        # check to see if we have a help screen
        app = self.getPhysicalRoot()
        try:
            app.restrictedTraverse(path)
        except (KeyError, Unauthorized):
            return ""
            
        url = "/HelpSys?help_url="+ "/".join(path)

        return """<a class="tabletitle" href="%s" \
            onClick="window.open('%s','zope_help','width=600,height=500, \
            menubar=yes,toolbar=yes,scrollbars=yes,resizable=yes');  \
            return false;" onMouseOver="window.status='Open online help'; \
            return true;" onMouseOut="window.status=''; return true;">Help!</a>
            """ % (url, url)



InitializeClass(ZenModelBase)
