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
        Call and return screen specified by zenScreenName value of REQUEST.
        If zenScreenName is not present call the default screen.  This is used
        in functions that are called from forms to get back to the correct
        screen with the correct context.
        """
        screenName = REQUEST.get("zenScreenName", "")
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
        if path.startswith("/"): path = path[1:]
        return self.getDmd().unrestrictedTraverse(path)
   

    def getZopeObj(self, path):
        "get object from path tat starts at zope root ie. /zport/dmd/Devices"
        return self.unrestrictedTraverse(path)


    def getNowString(self):
        """return the current time as a string"""
        return DateTime().strftime('%Y/%m/%d %H:%M:%S')


    def todayDate(self):
        """Return today's date as a string in the format 'mm/dd/yyyy'."""
        return DateTime().strftime("%m/%d/%Y")


    def yesterdayDate(self):
        """Return yesterday's date as a string in the format 'mm/dd/yyyy'."""
        yesterday = DateTime()-1
        return yesterday.strftime("%m/%d/%Y")


    
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
