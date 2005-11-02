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

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import travAndColl

from DeviceOrganizer import DeviceOrganizer


def manage_addSystem(context, id, description = None, REQUEST = None):
    """make a System"""
    d = System(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addSystem = DTMLFile('dtml/addSystem',globals())



class System(DeviceOrganizer):
    """
    System class is a device organizer that represents a business system.
    May need to manage "services" as well so that more sophisticated 
    dependencies can be tracked.
    """

    # Organizer configuration
    dmdRootName = "Systems"

    portal_type = meta_type = 'System'

    eventsField = "System"

    default_catalog = 'systemSearch'
    
    _properties = (
        {'id':'systemClass', 'type':'string', 'mode':'w'},
        {'id':'productionState', 'type':'keyedselection', 
            'mode':'w', 'select_variable':'getProdStateConversions'},
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 
    _relations = DeviceOrganizer._relations + (
        ("devices", ToMany(ToMany, "Device", "systems")),
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
                  permissions.view, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewSystemPerformance'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
         },
        )


    security = ClassSecurityInfo()

    def __init__(self, id,
                description = '',
                systemClass = '',
                productionState = 1000):
        DeviceOrganizer.__init__(self, id, description)
        self.productionState = productionState
        self.systemClass = systemClass


    security.declareProtected('View', 'omniPingStatus')
    def omniPingStatus(self):
        """pingStatus() -> return the number of devices that are down"""
        status = -1
        try:
            status = self.netcool.getPingStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except: pass
        return status
   

    security.declareProtected('View', 'omniCmtsPingStatus')
    def omniCmtsPingStatus(self):
        """omniCmtsPingStatus() -> return the number of ubrs that are down"""
        status = -1
        try:
            status = self.netcool.getOmniStatus(
                   systemName=self.getOrganizerName(),
                   where=" Class=100 and Severity=5 and Node like '.*cmts.*'")
            status = self.convertStatus(status)
        except: pass
        return status


    security.declareProtected('View', 'omniSnmpStatus')
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
