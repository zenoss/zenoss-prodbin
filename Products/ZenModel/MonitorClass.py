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
from Products.ZenUtils.Utils import checkClass
from ZenModelRM import ZenModelRM

from RRDTemplate import RRDTemplate

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())

from Products.ZenRelations.RelSchema import ToManyCont, ToOne


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
    _relations = ZenModelRM._relations + (
        ('rrdTemplates', ToManyCont(ToOne, 'Products.ZenModel.RRDTemplate', 'deviceClass')),
        )


    def __init__(self, id, title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)
        self.rrdTemplate = RRDTemplate()

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


    def manage_removeMonitor(self, ids = None, submon = None, REQUEST=None):
        'Add an object of sub_class, from a module of the same name'
        msg = ''
        child = self._getOb(submon) or self
        if ids:
            if len(ids) < len(child._objects):
                num = 0
                for id in ids:
                    if child.hasObject(id):
                        child._delObject(id)
                        num += 1
                msg = 'Deleted %s monitors' % num
                        
            else:
                msg = 'You must have at least one monitor'
        else:
            msg = 'No monitors are selected'
        if REQUEST:
            if msg:
                REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)


    def manage_addMonitor(self, id, submon=None, REQUEST=None):
        'Remove an object from this one'
        values = {}
        child = self._getOb(submon) or self
        exec('from Products.ZenModel.%s import %s' % (child.sub_class,
                                                      child.sub_class), values)
        ctor = values[child.sub_class]
        if id: child._setObject(id, ctor(id))
        if REQUEST: 
            REQUEST['message'] = 'Monitor created'
            return self.callZenScreen(REQUEST)


    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        for o in self.objectValues():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)


    def getAllRRDTemplates(self):
        "return the list of RRD Templates available at all levels"
        return self.rrdTemplates()


    def getRRDTemplates(self):
        "return the list of RRD Templates available at this level"
        return self.rrdTemplates()


    security.declareProtected('Add DMD Objects', 'manage_addRRDTemplate')
    def manage_addRRDTemplate(self, id, REQUEST=None):
        """Add an RRDTemplate to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        id = self.prepId(id)
        org = RRDTemplate(id)
        self.rrdTemplates._setObject(org.id, org)
        if REQUEST: 
            REQUEST['message'] = "Template added"
            return self.callZenScreen(REQUEST)
            

    def manage_copyRRDTemplates(self, ids=(), REQUEST=None):
        """Put a reference to the objects named in ids in the clip board"""
        if not ids: return self.callZenScreen(REQUEST)
        ids = [ id for id in ids if self.rrdTemplates._getOb(id, None) != None]
        if not ids: return self.callZenScreen(REQUEST)
        cp = self.rrdTemplates.manage_copyObjects(ids)
        if REQUEST:
            resp=REQUEST['RESPONSE']
            resp.setCookie('__cp', cp, path='/zport/dmd')
            REQUEST['__cp'] = cp
            REQUEST['message'] = "Templates copied"
            return self.callZenScreen(REQUEST)
        return cp


    def manage_pasteRRDTemplates(self, moveTarget=None, cb_copy_data=None, REQUEST=None):
        """Paste RRDTemplates that have been copied before.
        """
        cp = None
        if cb_copy_data: cp = cb_copy_data
        elif REQUEST:
            cp = REQUEST.get("__cp",None)
        
        if cp:
            if moveTarget:
                target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
            else:
                target = self
            target.rrdTemplates.manage_pasteObjects(cp)
        else:
            target = None
            
        if REQUEST:
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted', path='/zport/dmd',
                            expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            if target:
                message = "Template(s) moved to %s" % moveTarget
            else:
                message = None
            if not isinstance(REQUEST, FakeRequest):
                url = target.getPrimaryUrlPath() + '/perfConfig'
                if message:
                    url += '?message=%s' % message
                REQUEST['RESPONSE'].redirect(url)
            else:
                REQUEST['message'] = message
                return self.callZenScreen(REQUEST)


    def manage_copyAndPasteRRDTemplates(self, ids=(), copyTarget=None, REQUEST=None):
        ''' Copy the selected templates into the specified device class.
        '''
        if not ids:
            REQUEST['message'] = "No Templates Selected"
            return self.callZenScreen(REQUEST)
        if copyTarget is None:
            REQUEST['message'] = "No Target Selected"
            return self.callZenScreen(REQUEST)
        cp = self.manage_copyRRDTemplates(ids)
        return self.manage_pasteRRDTemplates(copyTarget, cp, REQUEST)


    def manage_deleteRRDTemplates(self, ids=(), paths=(), REQUEST=None):
        """Delete RRDTemplates from this DeviceClass 
        (skips ones in other Classes)
        """
        if not ids and not paths:
            return self.callZenScreen(REQUEST)
        for id in ids:
            if (getattr(aq_base(self), 'rrdTemplates', False)
                and getattr(aq_base(self.rrdTemplates),id,False)):
                self.rrdTemplates._delObject(id)
        if REQUEST: 
            REQUEST['message'] = "Templates deleted"
            return self.callZenScreen(REQUEST)

    def getSubDevicesGen(self):
        return []

    
InitializeClass(MonitorClass)
