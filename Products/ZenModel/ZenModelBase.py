################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenModelBase

$Id: ZenModelBase.py,v 1.17 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.17 $"[11:-2]

import copy

from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from Globals import InitializeClass
from Acquisition import aq_base, aq_chain
from DateTime import DateTime

from Products.CMFCore.utils import _verifyActionPermissions

from Products.ZenUtils.Utils import zenpathsplit, zenpathjoin 
from Products.ZenUtils.Utils import createHierarchyObj, getHierarchyObj


class ZenModelBase:
    """
    All ZenModel Persistent classes inherit from this class.  It profides
    some screen management functionality, and general utility methods.
    """

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

    
    def callZenScreen(self, REQUEST):
        """
        Call and return screen that was passed in the referer value of REQUEST
        """
        screenName = REQUEST['zenScreenName']
        #REQUEST['URL'] = "%s/%s" % (self.absolute_url_path(), screenName)
        screen = getattr(self, screenName, False)
        if not screen: 
            raise AttributeError("Screen %s not found in context %s" 
                                % (screenName, self.getPhysicalPath()))
        return screen()



    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
            '''return the breadcrumb links along a primary path'''
            links = []
            curDir = self.primaryAq()
            while curDir.id != terminator:
                if curDir.meta_type == 'ToManyContRelationship':
                    curDir = curDir.getPrimaryParent()
                    continue
                links.append(
                    (curDir.getPrimaryUrlPath(),
                    curDir.id))
                curDir = curDir.aq_parent

            links.reverse()
            return links
    
    
    security.declareProtected('View', 'confmonTabs')
    def zentinelTabs(self, templateName):
        '''return a list of hashs that define the screen tabs for this object'''
        tabs = []
        secman = getSecurityManager()
        urlbase = self.getPrimaryUrlPath()
        actions = self.factory_type_information[0]['actions']
        for a in actions:
            perm = a['permissions'][0] #just check first in list
            if (not a.get('visible', True) or
                not secman.checkPermission(perm, self)):
                continue
            a = a.copy()
            if a['action'] == templateName: a['selected'] = True
            tabs.append(a)
        return tabs

    
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
        from Products.ZenUtils.Utils import getObjByPath
        return getObjByPath(self.getDmd(), path)
   

    def getZopeObj(self, path):
        "get object from path tat starts at zope root ie. /zport/dmd/Devices"
        from Products.ZenUtils.Utils import getObjByPath
        return getObjByPath(self.getPhysicalRoot(), path)


    def getNowString(self):
        """return the current time as a string"""
        return DateTime().strftime('%Y/%m/%d %H:%M:%S')


InitializeClass(ZenModelBase)
