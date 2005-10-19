#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RouteEntry

RouteEntry represents a group of devices

$Id: IpRouteEntry.py,v 1.12 2004/04/12 16:33:15 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

import re

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from IpAddress import findIpAddress
from IpNetwork import addIpAddressToNetworks

from DeviceComponent import DeviceComponent
from DeviceResultInt import DeviceResultInt

def manage_addIpRouteEntry(context, id, title = None, REQUEST = None):
    """make a IpRouteEntry"""
    d = IpRouteEntry(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpRouteEntry = DTMLFile('dtml/addIpRouteEntry',globals())

class IpRouteEntry(DeviceComponent, DeviceResultInt):
    """IpRouteEntry object"""
    
    meta_type = 'IpRouteEntry'
    
    _properties = (
        {'id':'routemask', 'type':'string', 'mode':''},
        {'id':'nexthopip', 'type':'string', 
            'mode':'', 'setter':'setNextHopIp'},
        {'id':'routeproto', 'type':'string', 'mode':''},
        {'id':'routeage', 'type':'string', 'mode':''},
        {'id':'routetype', 'type':'string', 'mode':''},
        {'id':'metric1', 'type':'int', 'mode':''},
        {'id':'metric2', 'type':'int', 'mode':''},
        {'id':'metric3', 'type':'int', 'mode':''},
        {'id':'metric4', 'type':'int', 'mode':''},
        {'id':'metric5', 'type':'int', 'mode':''},
        ) 
    _relations = DeviceComponent._relations + (
        ("device", ToOne(ToManyCont,"Device","routes")),
        ("interface", ToOne(ToMany,"IpInterface","iproutes")),
        ("nexthop", ToOne(ToMany,"IpAddress","clientroutes")),
        )

    security = ClassSecurityInfo()

    ipcheck = re.compile(r'^127.|^0.').search

    def __init__(self, id, title = None):
        DeviceComponent.__init__(self, id, title)
        self._nexthop = ""
        self.routetype = ""
        self.routeproto = ""
        self.routemask = 0
        self.routeage = 0
        self.metric1 = 0
        self.metric2 = 0
        self.metric3 = 0
        self.metric4 = 0
        self.metric5 = 0
    

    def __getattr__(self, name):
        if name == 'nexthopip':
            return self.getNextHopIp()
        else:
            raise AttributeError, name
  

    security.declareProtected('View', 'getNextHopDeviceLink')
    def getNextHopDeviceLink(self):
        """figure out which hop to return and if its a relation build link"""
        ipobj = self.nexthop()
        retval = "" 
        if ipobj:
            retval = ipobj.getDeviceLink()
        if not retval: retval = "None"
        return retval
            
    
    security.declareProtected('View', 'getNextHopIp')
    def getNextHopIp(self):
        """get the proper nexthopip based on if it is stored locally or not"""
        ip = self._nexthop
        ipobj = self.nexthop()
        if ipobj: ip = ipobj.id
        return ip
  
    
    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        if self.interface():
            return self.interface().name
        return "No Interface"

       
    security.declareProtected('Change Device', 'setNextHopIp')
    def setNextHopIp(self, nextHopIp):
        """if the nexthop is a 127. or 0. address store locally
        else link to it in the network hierarchy"""
        if self.ipcheck(nextHopIp) or not nextHopIp:
            self._nexthop = nextHopIp
        else:
            ip = findIpAddress(self, nextHopIp)
            if not ip: 
                ip = addIpAddressToNetworks(self, nextHopIp)
            self.addRelation('nexthop', ip)
       
    
    security.declareProtected('Change Device', 'setInterface')
    def setInterface(self, interface):
        self.addRelation('interface', interface)


    def getInterface(self):
        return self.interface()


    security.declareProtected('View', 'getDevice')
    def getDevice(self):
        """get a routes device for DeviceResultInt"""
        return self.device()


InitializeClass(IpRouteEntry)
