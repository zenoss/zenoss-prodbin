#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""System

$Id: System.py,v 1.45 2004/04/14 22:11:48 edahl Exp $"""

__version__ = "$Revision: 1.45 $"[11:-2]

from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import permissions

from Products.ZenUtils.Utils import travAndColl

from DeviceGroupBase import DeviceGroupBase


def manage_addSystem(context, id, description = None, REQUEST = None):
    """make a System"""
    d = System(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addSystem = DTMLFile('dtml/addSystem',globals())



class System(DeviceGroupBase):
    """
    System class is a device organizer that represents a business system.
    May need to manage "services" as well so that more sophisticated 
    dependencies can be tracked.
    """

    # Organizer configuration
    dmdRootName = "Systems"
    dmdSubRel = "subsystems"

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
            'product'        : 'ZenModel',
            'factory'        : 'manage_addSystem',
            'immediate_view' : 'viewSystemStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewSystemStatus'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewSystemPerformance'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'systemEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'systemHistoryEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.ModifyPortalContent, )
                },
            )
         },
        )


    security = ClassSecurityInfo()

    def __init__(self, id,
                description = '',
                systemClass = '',
                productionState = 1000):
        DeviceGroupBase.__init__(self, id, description)
        self.productionState = productionState
        self.systemClass = systemClass


    def countDevices(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupBase.countDevices(self, "subsystems")

    
    def pingStatus(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupBase.pingStatus(self, "subsystems")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceGroupBase.snmpStatus(self, "subsystems")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceGroupBase.getSubDevices(self, filter, "subsystems")

    
    security.declareProtected('View', 'systemEvents')
    def systemEvents(self):
        """get the event list of this object"""
        return DeviceGroupBase.getDeviceGroupOmnibusEvents(self, "System")


    security.declareProtected('View', 'systemHistoryEvents')
    def systemHistoryEvents(self):
        """get the history event list of this object"""
        return DeviceGroupBase.getDeviceGroupOmnibusHistoryEvents(self, "System")
        
    
    security.declareProtected('View', 'omniPingStatus')
    def omniPingStatus(self):
        """pingStatus() -> return the number of devices that are down"""
        status = -1
        try:
            status = self.netcool.getPingStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except: pass
        return status
   

    security.declareProtected('View', 'cmtsPingStatus')
    def omniCmtsPingStatus(self):
        """cmtsPingStatus() -> return the number of ubrs that are down"""
        status = -1
        try:
            status = self.netcool.getOmniStatus(
                   systemName=self.getOrganizerName(),
                   where=" Class=100 and Severity=5 and Node like '.*cmts.*'")
            status = self.convertStatus(status)
        except: pass
        return status


    security.declareProtected('View', 'snmpStatus')
    def omniSnmpStatus(self):
        """snmpStatus() -> return the number of devices with snmp problems"""
        status = -1
        try:
            status = self.netcool.getSnmpStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except: pass
        return status


    security.declareProtected('View', 'eventCount')
    def omniEventCount(self):
        """eventCount() -> return the number of devices with snmp problems"""
        status = 0 
        try:
            status = self.netcool.getEventCount(system=self.getOrganizerName())
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
        return self.getOrganizerName() + " " + self.description
    

    security.declareProtected('View', 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        
        if self.prodStateConversions:
            for line in self.prodStateConversions: #aq
                line = line.rstrip()
                (sev, num) = line.split(':')
                if int(num) == prodState:
                    return sev
        return "Unknown"


        
InitializeClass(System)
