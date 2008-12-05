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

__doc__="""RouteEntry

RouteEntry represents a group of devices
"""

import re

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import localIpCheck, prepId
from Products.ZenRelations.RelSchema import *


from OSComponent import OSComponent

import logging
log = logging.getLogger("zen.IpRouteEntry")

def manage_addIpRouteEntry(context, dest, routemask, nexthopid, interface, 
                   routeproto, routetype, userCreated=None, REQUEST = None):
    """
    Make a IpRouteEntry from the ZMI
    """
    if not routemask:
        routemask = 0
    else:
        routemask = int(routemask)
    dest = '%s/%s' % (dest, routemask)
    id = prepId(dest)
    d = IpRouteEntry(id)
    context._setObject(id, d)
    d = context._getOb(id)
    d.setTarget(dest)
    d.setNextHopIp(nexthopid)
    d.setInterfaceName(interface)
    if userCreated: d.setUserCreateFlag()
    d.routeproto = routeproto
    d.routetype = routetype
    d.routemask = routemask
    
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpRouteEntry = DTMLFile('dtml/addIpRouteEntry',globals())


class IpRouteEntry(OSComponent):
    """
    IpRouteEntry object
    """
    
    meta_type = 'IpRouteEntry'

    # we don't monitor routes
    monitor = False
    
    _nexthop = ""
    _target = ""
    _targetobj = None
    routetype = ""
    routeproto = ""
    routemask = 0
    routeage = 0
    metric1 = 0
    metric2 = 0
    metric3 = 0
    metric4 = 0
    metric5 = 0

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
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","routes")),
        ("interface", ToOne(ToMany,"Products.ZenModel.IpInterface","iproutes")),
        ("nexthop", ToOne(ToMany,"Products.ZenModel.IpAddress","clientroutes")),
        ("target", ToOne(ToMany,"Products.ZenModel.IpNetwork","clientroutes")),
        )

    security = ClassSecurityInfo()

    ipcheck = re.compile(r'^127\.|^0\.0\.|^169\.254\.|^224\.').search

    
    def __getattr__(self, name):
        """
        Allow access to getNextHopIp() though the nexthopip attribute
        """
        if name == 'nexthopip':
            return self.getNextHopIp()
        else:
            raise AttributeError( name )
  

    security.declareProtected('View', 'getNextHopDeviceLink')
    def getNextHopDeviceLink(self):
        """
        Figure out which hop to return and if its a relation build link
        """
        ipobj = self.nexthop()
        retval = "" 
        if ipobj:
            retval = ipobj.getDeviceLink()
        if not retval: retval = "None"
        return retval
            

    def getNextHopIpLink(self):
        """
        Return an <a> link to our next hop ip.
        """
        ipobj = self.nexthop()
        if not ipobj: return ""
        return ipobj.getPrimaryLink()

        
    security.declareProtected('View', 'getNextHopIp')
    def getNextHopIp(self):
        """
        Return our next hop ip (as string) if stored as object or locally.
        """
        ip = self._nexthop
        ipobj = self.nexthop()
        if ipobj: ip = ipobj.id
        return ip
 

    def getNextHopDevice(self):
        """
        Return the device to which this route points.
        """
        ipobj = self.nexthop()
        if ipobj: return ipobj.device()
        
    
    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """
        Return the interface name for this route as a string.
        If no interface is found return 'No Interface'.
        """
        if self.interface():
            return self.interface().name()
        return "No Interface"

       
    security.declareProtected('Change Device', 'setNextHopIp')
    def setNextHopIp(self, nextHopIp):
        """
        If the nexthop is a 127. or 0. address store locally
        else link to it in the network hierarchy
        """
        if localIpCheck(self, nextHopIp) or not nextHopIp:
            self._nexthop = nextHopIp
        else:
            networks = self.device().getNetworkRoot()
            ip = networks.findIp(nextHopIp)
            if not ip: 
                netmask = 24
                int = self.interface()
                if int: 
                    intip = int.getIpAddressObj()
                    if intip: netmask = intip.netmask
                ip = networks.createIp(nextHopIp, netmask)
            self.addRelation('nexthop', ip)
      

    def matchTarget(self, ip):
        """
        Does this route target match the ip passed.
        """
        if self.target(): return self.target().hasIp(ip)      
            
    
    def setTarget(self, netip):
        """
        Set this route target netip in the form 10.0.0.0/24.
        """
        netid, netmask = netip.split('/')
        if localIpCheck(self, netip) or netmask == '0':
            self._target = netip
        else:
            networks = self.device().getNetworkRoot()
            net = networks.createNet(netid, netmask)
            self.target.addRelation(net)


    def getTarget(self):
        """
        Return the route target ie 0.0.0.0/0.
        """
        if self.target():
            return self.target().getNetworkName()
        else:
            return self._target


    def getTargetIp(self):
        """
        Return the target network Ip ie: 10.2.1.0
        """
        return self.getTarget().split("/")[0]

        
    def getTargetLink(self):
        """
        Return an <a> link to our target network.
        """
        if self.target(): 
            return self.target().urlLink()
        else:
            return self._target


    security.declareProtected('Change Device', 'setInterfaceIndex')
    def setInterfaceIndex(self, ifindex):
        """
        Set the interface relationship to the interface specified by the given
        index.  See also setInterfaceName()
        """
        for int in self.os().interfaces():
            if int.ifindex == ifindex: break
        else:
            int = None
        if int: self.interface.addRelation(int)
        else: log.warn("interface index:%s not found", ifindex)


    def getInterfaceIndex(self):
        """
        Return the index of the associated interface or None if no
        interface is found.
        """
        int = self.interface()
        if int: return int.ifindex


    security.declareProtected('Change Device', 'setInterfaceName')
    def setInterfaceName(self, intname):
        """
        Set the interface relationship to the interface specified by the given
        name.  See also setInterfaceIndex()
        """
        try:
            int = filter(lambda i: i.name() == intname,
                    self.os().interfaces())[0]
            self.interface.addRelation(int)
        except IndexError:
            log.warn("interface '%s' not found", intname)


    def getInterfaceIp(self):
        """
        Retrieve ip of the associated interface
        """
        int = self.interface()
        if int: return int.getIp()
        return ""


InitializeClass(IpRouteEntry)
