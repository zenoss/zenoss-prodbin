#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""System

System represents a group of devices that provide a major
business function

$Id: System.py,v 1.45 2004/04/14 22:11:48 edahl Exp $"""

__version__ = "$Revision: 1.45 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Products.ZenUtils.Utils import travAndColl

from Instance import Instance
from DeviceGroupInt import DeviceGroupInt


def manage_addSystem(context, id, title = None, REQUEST = None):
    """make a System"""
    d = System(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSystem = DTMLFile('dtml/addSystem',globals())

class System(Instance, DeviceGroupInt):
    """System object"""
    portal_type = meta_type = 'System'
    default_catalog = 'systemSearch'
    
    _properties = (
                    {'id':'systemClass', 'type':'string', 'mode':'w'},
                    {'id':'productionState', 'type':'keyedselection', 
                        'mode':'w', 'select_variable':'getProdStateConversions'},
                    {'id':'description', 'type':'text', 'mode':'w'},
                   ) 

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'System',
            'meta_type'      : 'System',
            'description'    : """Base class for all devices""",
            'icon'           : 'System_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addSystem',
            'immediate_view' : 'viewSystemStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewSystemStatus'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewSystemPerformance'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'systemEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'systemHistoryEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.ModifyPortalContent, )
                },
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewItem'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
         },
        )


    security = ClassSecurityInfo()

    def __init__(self, id,
                description = '',
                systemClass = '',
                productionState = 1000):
        Instance.__init__(self, id)
        self.description = description
        self.productionState = productionState
        self.systemClass = systemClass


    def getSystemName(self):
        """walk up our parent path to build the full name of this system"""
        return DeviceGroupInt.getDeviceGroupName(self)

    getPathName = getFullSystemName = getSystemName


    def getSystemNames(self):
        """return the full path names to all subsystems"""
        return DeviceGroupInt.getDeviceGroupNames(self,subrel="subsystems")


    def countDevices(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.countDevices(self, "subsystems")

    
    def pingStatus(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.pingStatus(self, "subsystems")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceGroupInt.snmpStatus(self, "subsystems")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceGroupInt.getSubDevices(self, filter, "subsystems")

    
    security.declareProtected('View', 'systemEvents')
    def systemEvents(self):
        """get the event list of this object"""
        return DeviceGroupInt.getDeviceGroupOmnibusEvents(self, "System")


    security.declareProtected('View', 'systemHistoryEvents')
    def systemHistoryEvents(self):
        """get the history event list of this object"""
        return DeviceGroupInt.getDeviceGroupOmnibusHistoryEvents(self, "System")
        
    
    security.declareProtected('View', 'omniPingStatus')
    def omniPingStatus(self):
        """pingStatus() -> return the number of devices that are down"""
        status = -1
        try:
            status = self.netcool.getPingStatus(system=self.getFullSystemName())
            status = self.convertStatus(status)
        except: pass
        return status
   

    security.declareProtected('View', 'cmtsPingStatus')
    def omniCmtsPingStatus(self):
        """cmtsPingStatus() -> return the number of ubrs that are down"""
        status = -1
        try:
            status = self.netcool.getOmniStatus(
                   systemName=self.getFullSystemName(),
                   where=" Class=100 and Severity=5 and Node like '.*cmts.*'")
            status = self.convertStatus(status)
        except: pass
        return status


    security.declareProtected('View', 'snmpStatus')
    def omniSnmpStatus(self):
        """snmpStatus() -> return the number of devices with snmp problems"""
        status = -1
        try:
            status = self.netcool.getSnmpStatus(system=self.getFullSystemName())
            status = self.convertStatus(status)
        except: pass
        return status


    security.declareProtected('View', 'eventCount')
    def omniEventCount(self):
        """eventCount() -> return the number of devices with snmp problems"""
        status = 0 
        try:
            status = self.netcool.getEventCount(system=self.getFullSystemName())
        except: pass
        return status


    def getDeviceMetaTypes(self):
        '''Build the list of meta types
        for devices in the device relationship'''
        meta_types = {}
        for dev in self.devices():
            if not meta_types.has_key(dev.meta_type):
                meta_types[dev.meta_type] = []
            meta_types[dev.meta_type].append(dev)
        return meta_types


    def summary(self):
        """text summary of object for indexing"""
        return self.getFullSystemName() + " " + self.description
                

        
InitializeClass(System)
