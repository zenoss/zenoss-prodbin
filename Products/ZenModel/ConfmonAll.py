################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ConfmonAll

All Confmon Data object inherit from this class it is a 
mix in class that provides common functionality to ConfmonBase 
and ConfmonItem (non relationship manager data)

$Id: ConfmonAll.py,v 1.17 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.17 $"[11:-2]

import copy

from AccessControl import ClassSecurityInfo, getSecurityManager
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime

from Products.CMFCore.utils import _verifyActionPermissions

from Products.ZenUtils.Utils import zenpathsplit, zenpathjoin, getHierarchyObj


class ConfmonAll:
    security = ClassSecurityInfo()

    def __hash__(self):
        return hash(self.id)


    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
            '''return the breadcrumb links along a primary path'''
            links = []
            curDir = self.primaryAq()
            while curDir.id != terminator:
                if curDir.meta_type == 'To Many Relationship':
                    curDir = curDir.aq_parent
                    continue
                links.append(
                    (curDir.getPrimaryUrlPath(),
                    curDir.id))
                curDir = curDir.aq_parent

            links.reverse()
            return links
    
    
    security.declareProtected('View', 'confmonTabs')
    def confmonTabs(self):
        '''return a list of hashs that define the screen tabs for this object'''
        typeInfo = self.getTypeInfo()
        if typeInfo:
            actions = copy.deepcopy(typeInfo.getActions())
        else:
            actions = copy.deepcopy(self.factory_type_information[0]['actions'])
        tabs = []
        secman = getSecurityManager()
        urlbase = self.getPrimaryUrlPath()
        for a in actions:
            perm = a['permissions'][0] #just check first in list
            if ((a.has_key('visible') and not a['visible']) or
                not secman.checkPermission(perm, self)):
                continue
            tabs.append(a) 
        return self.selectedTab(tabs, self.REQUEST['URL'])

    
    def selectedTab(self, tabs, url):
        """figure out which tab is currently selected if non have been clicked
        set first tab to selected"""
        for tab in tabs:
            if url.find(tab['action']) > 0:
                tab['selected'] = 1
                break
        else:
            tabs[0]['selected'] = 1
        return tabs
        

        
    def __call__(self):
        '''
        Invokes the default view.
        '''
        #from Products.ZenModel.Instance import Instance
        #if isinstance(self, Instance):
        #    return self.restrictedTraverse("viewItem")()
        actions = []
        view = "view"
        ti = self.getTypeInfo()
        if not ti:
            if hasattr(self, "factory_type_information"):
                view = self.factory_type_information[0]['immediate_view']
                actions = self.factory_type_information[0]['actions']
            else:
                raise 'Not Found', ('Cannot find default view for "%s"' %
                                    '/'.join(self.getPhysicalPath()))
        else:
            view = ti.immediate_view
            actions = ti.getActions()
        try:
            return self.restrictedTraverse(view)()
        except KeyError: pass
        for action in actions:
            if action.get('id', None) == view:
                if _verifyActionPermissions(self, action):
                    return self.restrictedTraverse(action['action'])()
        # "view" action is not present or not allowed.
        # Find something that's allowed.
        for action in actions:
            if _verifyActionPermissions(self, action):
                return self.restrictedTraverse(action['action'])()
        raise 'Unauthorized', ('No accessible views available for %s' %
                               '/'.join(self.getPhysicalPath()))



    index_html = None  # This special value informs ZPublisher to use __call__


    security.declareProtected('View', 'view')
    def view(self):
        '''
        Returns the default view even if index_html is overridden.
        '''
        return self()

    
    security.declareProtected('View', 'mainframeView')
    def mainframeView(self):
        """get the default view for the mainframe of an object 
        used by index.zpt"""
        url = self.absolute_url()
        actions = self.factory_type_information[0].get('actions',None)
        if actions:
            return url + '/' + actions[0]['action']


    security.declareProtected('View', 'topframeView')
    def topframeView(self):
        """get the default view for the mainframe of an object 
        used by index.zpt"""
        return self.absolute_url() + "/top"


    def getPrimaryFullId(self):
        """get the full dmd id of this object strip off everything before dmd"""
        path = list(self.getPrimaryPath())
        index = path.index('dmd')+1
        return '/'+'/'.join(path[index:])
  

    def zenpathjoin(self, path):
        return zenpathjoin(path)


    def zenpathsplit(self, path):
        return zenpathsplit(path)


    def getHierarchyObj(self, root, name, factory, lastfactory=None, 
                    relpath=None, lastrelpath=None, log=None):
        return getHierarchyObj(root, name, factory, 
                                lastfactory, relpath, lastrelpath, log)


    def getDmd(self):
        """return the dmd root object"""
        if hasattr(self, 'aq_chain'):
            aqchain = self.aq_chain
            for obj in aqchain:
                if obj.id == 'dmd': return obj
            

    def getOrganizer(self, name):
        """return an organizer object by its name"""
        dmd = self.getDmd()
        if hasattr(dmd, name):
            return getattr(dmd, name)
        else:
            raise AttributeError, "Organizer %s not found in DMD" % name

    
    def getDmdObj(self, path):
        """get object from path that starts at dmd ie. /Devices/Servers/box"""
        from Products.ZenUtils.Utils import getObjByPath
        return getObjByPath(self.getDmd(), path)
   

    def getZopeObj(self, path):
        "get object from path tat starts at zope root ie. /zport/dmd/Devices"
        from Products.ZenUtils.Utils import getObjByPath
        return getObjByPath(self.getPhysicalRoot(), path)


    def exceptMsg(self):
        """format the exception information to be used in logging"""
        import traceback
        import cStringIO
        sio = cStringIO.StringIO()
        traceback.print_exc(None,sio)
        return sio.getvalue()
   

    def getNowString(self):
        """return the current time as a string"""
        return DateTime().strftime('%Y/%m/%d %H:%M:%S')


InitializeClass(ConfmonAll)
