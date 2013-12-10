
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""MonitorClass

Organizes Monitors

$Id: MonitorClass.py,v 1.11 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision$"[11:-2]

from BTrees.OOBTree import OOBTree
from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_base
from OFS.Folder import Folder
from Products.ZenUtils.Utils import checkClass
from ZenModelRM import ZenModelRM
from Products.ZenWidgets import messaging

from RRDTemplate import RRDTemplate
from TemplateContainer import TemplateContainer

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())


class MonitorClass(ZenModelRM, Folder, TemplateContainer):
    #isInTree = 1
    meta_type = "MonitorClass"
    sub_class = 'MonitorClass'
    dmdRootName = 'Monitors'

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
    _relations = TemplateContainer._relations

    def __init__(self, id, title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)
        self.prevCollectorPerDevice = OOBTree()

    def setPreviousCollectorForDevice(self, device_id, collector):
        """
        Sets the previous collector for a device.
        The previous collector for each device is stored in an OOBTree
        This info is stored in order to make invalidations more efficient.
        Now, when moving a device between collectors, invalidations will 
        only be sent to the current collector and to the previous collector.
        """
        if not hasattr(self, 'prevCollectorPerDevice'):
            self.prevCollectorPerDevice = OOBTree()
        self.prevCollectorPerDevice[device_id] = collector

    def getPreviousCollectorForDevice(self, device_id):
        """ Returns the previous collector for a device """
        prev_collector = None
        if hasattr(self, 'prevCollectorPerDevice'):
            prev_collector = self.prevCollectorPerDevice.get(device_id, None)
        return prev_collector

    def deletePreviousCollectorForDevice(self, device_id):
        """ Deletes the previos collector info for a device """
        if hasattr(self, 'prevCollectorPerDevice') and device_id in self.prevCollectorPerDevice:
            del self.prevCollectorPerDevice[device_id]

    def getBreadCrumbName(self):
        return 'Collectors'

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
        return sorted(perfServer.objectIds(spec=('PerformanceConf')))


    def objectSubValues(self):
        """get contained objects that are sub classes of sub_class"""
        return [obj for obj in self.objectValues()
                    if checkClass(obj.__class__, self.sub_class)]


    security.declareProtected('Manage DMD', 'manage_removeMonitor')
    def manage_removeMonitor(self, ids = None, submon = "", REQUEST=None):
        'Add an object of sub_class, from a module of the same name'
        msg = ''
        if isinstance(ids, basestring):
            ids = (ids,)
        child = self._getOb(submon, self) 
        if ids:
            if len(ids) < len(child._objects):
                num = 0
                for id in ids:
                    if child.hasObject(id):
                        child._delObject(id)
                        num += 1
                messaging.IMessageSender(self).sendToBrowser(
                    'Collectors Deleted',
                    'Deleted collectors: %s' % (', '.join(ids))
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'You must have at least one collector.',
                    priority=messaging.WARNING
                )
        else:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'No collectors were selected.',
                priority=messaging.WARNING
            )
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected('Manage DMD', 'manage_addMonitor')
    def manage_addMonitor(self, id, submon=None, REQUEST=None):
        'Remove an object from this one'
        values = {}
        child = self._getOb(submon) or self
        exec('from Products.ZenModel.%s import %s' % (child.sub_class,
                                                      child.sub_class), values)
        ctor = values[child.sub_class]
        if id: child._setObject(id, ctor(id))
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Monitor Created',
                'Monitor %s was created.' % id
            )
            return self.callZenScreen(REQUEST)


    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        for o in self.objectValues():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)


    def getAllRRDTemplates(self):
        """
        Return a list of all RRDTemplates at this level and below.
        
        Note: DeviceClass.getAllRRDTemplates has been rewritted to
        use the searchRRDTemplates catalog.  Because there is only
        one level of MonitorClass this approach might be overkill for
        this situation.  However, if MonitorClasses ever become
        hierarchical and contain many RRDTemplates it should probably
        be refactored in a similar way.
        """
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
            messaging.IMessageSender(self).sendToBrowser(
                'Template Added',
                'Template %s was created.' % id
            )
            return self.callZenScreen(REQUEST)


    def manage_deleteRRDTemplates(self, ids=(), paths=(), REQUEST=None):
        """Delete RRDTemplates from this MonitorClass
        (skips ones in other Classes)
        """
        if not ids and not paths:
            return self.callZenScreen(REQUEST)
        for id in ids:
            self.rrdTemplates._delObject(id)
        for path in paths:
            id = path.split('/')[-1]
            self.rrdTemplates._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Deleted',
                'Templates were deleted: %s' % (', '.join(ids))
            )
            return self.callZenScreen(REQUEST)

    def getSubDevicesGen(self):
        return []


InitializeClass(MonitorClass)
