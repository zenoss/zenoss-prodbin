#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""MonitorClass

The service classification class.  default identifiers, screens,
and data collectors live here.

$Id: MonitorClass.py,v 1.11 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())

class MonitorClass(Classification, Folder):
    meta_type = "MonitorClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options


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
            


InitializeClass(MonitorClass)
