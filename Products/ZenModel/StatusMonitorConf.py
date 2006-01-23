#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""StatusMonitorConf

The configuration object for monitors.

$Id: StatusMonitorConf.py,v 1.40 2004/04/22 02:13:23 edahl Exp $"""

__version__ = "$Revision: 1.40 $"[11:-2]

import re
import logging

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime

from zLOG import LOG, WARNING

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Monitor import Monitor
from Products.ZenModel.StatusColor import StatusColor
from Products.ZenModel.ZenDate import ZenDate


def manage_addStatusMonitorConf(context, id, title = None, REQUEST = None):
    """make a monitor"""
    dc = StatusMonitorConf(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addStatusMonitorConf = DTMLFile('dtml/addStatusMonitorConf',globals())

class StatusMonitorConf(Monitor, StatusColor):
    '''Configuration for monitors'''
    portal_type = meta_type = "StatusMonitorConf"

    monitorRootName = "StatusMonitors"

    _properties = (
        {'id':'chunk','type':'int','mode':'w'},
        {'id':'timeOut','type':'float','mode':'w'},
        {'id':'tries','type':'int','mode':'w'},
        {'id':'snmpTimeOut','type':'float','mode':'w'},
        {'id':'snmpTries','type':'int','mode':'w'},
        {'id':'cycleInterval','type':'int','mode':'w'},
        {'id':'snmpCycleInterval','type':'int','mode':'w'},
        {'id':'cycleFailWarn','type':'int','mode':'w'},
        {'id':'cycleFailCritical','type':'int','mode':'w'},
        {'id':'configCycleInterval','type':'int','mode':'w'},
        {'id':'maxFailures','type':'int','mode':'w'},
        {'id':'prodStateThreshold','type':'int','mode':'w'},
        )
    _relations = (
        ("devices", ToMany(ToMany,"Device","monitors")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'StatusMonitorConf',
            'meta_type'      : 'StatusMonitorConf',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'StatusMonitorConf_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addStatusMonitorconf',
            'immediate_view' : 'viewStatusMonitorOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewStatusMonitorOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editStatusMonitorConf'
                , 'permissions'   : ("Manage DMD",)
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

    def __init__(self, id, title=None,
                chunk=75,
                timeOut=1.5,
                tries=2,
                snmpTimeOut=3.0,
                snmpTries=2,
                cycleInterval=60,
                snmpCycleInterval=60,
                configCycleInterval=20,
                maxFailures = 1440,
                cycleFailWarn = 2,
                cycleFailCritical = 3
                ):
        '''Create a  monitor configuration'''
        Monitor.__init__(self, id, title)
        self.chunk = chunk
        self.timeOut = timeOut
        self.tries = tries
        self.snmpTimeOut = snmpTimeOut
        self.snmpTries = snmpTries
        self.cycleInterval = cycleInterval
        self.snmpCycleInterval = snmpCycleInterval
        self.configCycleInterval = configCycleInterval
        self.maxFailures = maxFailures
        self.cycleFailWarn = cycleFailWarn
        self.cycleFailCritical = cycleFailCritical
        self.prodStateThreshold = 1000


    security.declareProtected('View','getPathName')
    def getPathName(self):
        return self.id

    security.declareProtected('View','getChunk')
    def getChunk(self):
        '''get the chunk size'''
        return self.chunk

    security.declareProtected('View','getTimeOut')
    def getTimeOut(self):
        '''get the timeout length'''
        return self.timeOut

    security.declareProtected('View','getTries')
    def getTries(self):
        '''get the number of times to try on failure'''
        return self.tries

    security.declareProtected('View','getTimeOut')
    def getSnmpTimeOut(self):
        '''get the timeout length'''
        if not hasattr(self, 'snmpTimeOut'):
            self.snmpTimeOut=3.0
        return self.snmpTimeOut

    security.declareProtected('View','getTries')
    def getSnmpTries(self):
        '''get the number of times to try on failure'''
        if not hasattr(self, 'snmpTies'):
            self.snmpTies=2
        return self.snmpTries

    security.declareProtected('View','getCycleInterval')
    def getCycleInterval(self):
        '''get the number of seconds between  sweeps'''
        return self.cycleInterval

    security.declareProtected('View','getSnmpCycleInterval')
    def getSnmpCycleInterval(self):
        '''get the number of seconds between snmp sweeps'''
        return self.snmpCycleInterval

    security.declareProtected('View','getConfigCycleInterval')
    def getConfigCycleInterval(self):
        '''get the number of seconds between sweeps'''
        return self.configCycleInterval

    security.declareProtected('View','getCycleFailWarn')
    def getCycleFailWarn(self):
        '''get the number of seconds between  sweeps'''
        if not hasattr(self, 'cycleFailWarn'):
            self.cycleFailWarn=2
        return self.cycleFailWarn


    security.declareProtected('View','getCycleFailCritical')
    def getCycleFailCritical(self):
        '''get the number of seconds between  sweeps'''
        if not hasattr(self, 'cycleFailCritical'):
            self.cycleFailCritical=3
        return self.cycleFailCritical


    security.declareProtected('View','getMaxFailures')
    def getMaxFailures(self):
        "return the number of failures allowed for a device"
        return self.maxFailures


    security.declareProtected('View','getPingDevices')
    def getPingDevices(self):
        '''get the devices associated with this
         monitor configuration'''
        devices = []
        for dev in self.devices.objectValuesAll():
            try:
                if dev.productionState >= self.prodStateThreshold:
                    dev = dev.primaryAq()
                    devices.append(dev)
                    #devices += self.getExtraPingInterfaces(dev)
            except:
                msg = "exception getting device %s\n" % dev.getId()
                logging.exception(msg)
        return devices


    security.declareProtected('View','getExtraPingInterfaces')
    def getExtraPingInterfaces(self, dev):
        """collect other interfaces to ping based on 
        aquired value pingInterfaceSpecifications"""
        intDescr = getattr(dev, 'zPingInterfaceDescription', None)
        intName = getattr(dev, 'zPingInterfaceName', None)
        catalog = getattr(dev, 'interfaceSearch', None)
        interfaces = {}
        if catalog:
            results = []
            if intName:
                namequery = {}
                namequery['deviceName'] = dev.getId()
                namequery['interfaceName'] = intName
                results += catalog(namequery)
            if intDescr:
                descrquery = {}
                descrquery['deviceName'] = dev.getId()
                descrquery['description'] = intDescr
                results += catalog(descrquery)
            for result in results:
                int = self.getZopeObj(result.getPrimaryUrlPath)
                if (int and int.adminStatus == 1 
                    and not interfaces.has_key(int)): 
                    ip = int.getIp()
                    if ip:
                        name = dev.getId() + ":" + int.getId()
                        interfaces[int] = (
                                name,
                                ip,
                                int.absolute_url(),
                                int.getPingStatusNumber())
        return interfaces.values()


    security.declareProtected('View','getSnmpDevices')
    def getSnmpDevices(self):
        '''get the devices associated with this
         monitor configuration'''
        devices = []
        for dev in self.devices.objectValuesAll():
            try:
                dev = dev.primaryAq()
                if getattr(dev, "zSnmpMonitorIgnore", False): continue
                ipaddr = dev.getManageIp()
                url = dev.absolute_url()
                if (dev.productionState >= self.prodStateThreshold
                    and dev.zSnmpCommunity):
                   devices.append(( 
                        dev.id, url, ipaddr
                        dev.getSnmpStatusNumber(),
                        dev.zSnmpCommunity,
                        dev.zSnmpPort))
            except:
                msg = "exception getting device %s\n" % dev.getId()
                logging.exception(msg)
        return devices
   

    security.declareProtected('View','updateSnmpDevices')
    def updateSnmpDevices(self, devices):
        '''process the snmp status information form the snmpmonitor'''
        for url, uptime in devices:
            try:
                path = url.split('/')[3:]
                device = self.getZopeObj(path)
                if device and uptime:
                    device.setSnmpUpTime(long(uptime))
            except:
                msg = "error updating device %s\n" % dev.getId()
                logging.exception(msg)
                    
  
    def getPingHeartbeat(self):
        """return ping heartbeat object"""
        return self.pingHeartbeat


    def getPingHeartbeatString(self):
        return self.pingHeartbeat.getString()


    def getSnmpHeartbeat(self):
        """return snmp heartbeat object"""
        return self.snmpHeartbeat


    def getSnmpHeartbeatString(self):
        return self.snmpHeartbeat.getString()


    security.declareProtected('Manage Device Status', 'setPingHeartbeat')
    def setPingHeartbeat(self):
        """set the last time the ping monitor ran"""
        self.pingHeartbeat.setDate()


    security.declareProtected('Manage Device Status', 'setSnmpHeartbeat')
    def setSnmpHeartbeat(self):
        """set the last time the snmp monitor ran"""
        self.snmpHeartbeat.setDate()

    
    security.declareProtected('Manage DMD', 'manage_editStatusMonitorConf')
    def manage_editStatusMonitorConf(self, 
                    chunk=75,timeOut=1.5,tries=2,
                    snmpTimeOut=3.0,snmpTries=2,
                    cycleInterval=60,snmpCycleInterval=60,
                    configCycleInterval=20,
                    cycleFailWarn=2,cycleFailCritical=3,
                    maxFailures=1440,prodStateThreshold=1000, REQUEST=None):
        """
        Edit a StatusMonitorConf from a web page.
        """
        self.chunk = chunk
        self.timeOut = timeOut
        self.tries = tries
        self.snmpTimeOut = snmpTimeOut
        self.snmpTries = snmpTries
        self.cycleInterval = cycleInterval
        self.snmpCycleInterval = snmpCycleInterval
        self.configCycleInterval = configCycleInterval
        self.cycleFailWarn = cycleFailWarn
        self.cycleFailCritical = cycleFailCritical
        self.maxFailures = maxFailures
        self.prodStateThreshold = prodStateThreshold
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST)


InitializeClass(StatusMonitorConf)
