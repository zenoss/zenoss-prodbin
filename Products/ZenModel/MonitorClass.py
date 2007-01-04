#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""MonitorClass

Organizes Monitors

$Id: MonitorClass.py,v 1.11 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision$"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_base
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenUtils.Utils import checkClass
from ZenModelRM import ZenModelRM

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())

class MonitorClass(ZenModelRM, Folder):
    #isInTree = 1
    meta_type = "MonitorClass"
    sub_class = 'MonitorClass'

    _properties = (
        {'id':'title', 'type':'string', 'mode':'w'},
        {'id':'sub_class', 'type':'string', 'mode':'w'},
        {'id':'sub_meta_types', 'type':'lines', 'mode':'w'},
    )

    factory_type_information = ( 
        { 
            'id'             : 'MonitorClass',
            'meta_type'      : meta_type,
            'description'    : "Monitor Class",
            'icon'           : 'Classification_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addMonitorClass',
            'immediate_view' : 'monitorList',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'monitorList'
                , 'permissions'   : (
                  permissions.view, )
                , 'visible'       : 0
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    def getStatusMonitor(self, monitorName):
        """get or create the status monitor name"""
        from Products.ZenModel.StatusMonitorConf \
            import manage_addStatusMonitorConf
        statusMonitorObj = self.getDmdRoot("Monitors").StatusMonitors
        if not hasattr(statusMonitorObj, monitorName):
            manage_addStatusMonitorConf(statusMonitorObj, monitorName)
        return statusMonitorObj._getOb(monitorName)


    def getStatusMonitorNames(self):
        """return a list of all status monitor names"""
        status = self.getDmdRoot("Monitors").StatusMonitors
        snames = status.objectIds()
        snames.sort()
        return snames

    def getPerformanceMonitor(self, monitorName):
        """get or create the performance monitor name"""
        from Products.ZenModel.PerformanceConf \
            import manage_addPerformanceConf
        perfServerObj = self.getDmdRoot("Monitors").Performance
        if not hasattr(perfServerObj, monitorName):
            manage_addPerformanceConf(perfServerObj, monitorName)
        return perfServerObj._getOb(monitorName)


    def getPerformanceMonitorNames(self):
        """return a list of all performance monitor names"""
        perfServer = self.getDmdRoot("Monitors").Performance
        cnames = perfServer.objectIds()
        cnames.sort()
        return cnames
            

    def objectSubValues(self):
        """get contained objects that are sub classes of sub_class"""
        retdata = []
        for obj in self.objectValues():
            if checkClass(obj.__class__, self.sub_class):
                retdata.append(obj)
        return retdata


    def manage_removeMonitor(self, ids = None, REQUEST=None):
        'Add an object of sub_class, from a module of the same name'
        if ids:
            for id in ids:
                if self.hasObject(id):
                    self._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def manage_addMonitor(self, id, REQUEST=None):
        'Remove an object from this one'
        values = {}
        exec('from Products.ZenModel.%s import %s' % (self.sub_class,
                                                      self.sub_class), values)
        ctor = values[self.sub_class]
        if id: self._setObject(id, ctor(id))
        if REQUEST: return self.callZenScreen(REQUEST)

InitializeClass(MonitorClass)
