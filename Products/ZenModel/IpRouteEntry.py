#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
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

from Products.ZenUtils.Utils import localIpCheck, prepId
from Products.ZenRelations.RelSchema import *

from IpAddress import findIpAddress

from OSComponent import OSComponent

import logging
log = logging.getLogger("zen.IpRouteEntry")

def manage_addIpRouteEntry(context, dest, nexthopid, interface, routeproto, routetype, userCreated=None, REQUEST = None):
    """make a IpRouteEntry"""
    id = prepId(dest)
    d = IpRouteEntry(id)
    context._setObject(id, d)
    d = context._getOb(id)
    d.setTarget(dest)
    d.setNextHopIp(nexthopid)
    d.setInterfaceName(interface)
    if userCreated: d.setUserCreateFlag()
    setattr(d, 'routeproto', routeproto)
    setattr(d, 'routetype', routetype)
    
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpRouteEntry = DTMLFile('dtml/addIpRouteEntry',globals())

class IpRouteEntry(OSComponent):
    """IpRouteEntry object"""
    
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
            

    def getNextHopIpLink(self):
        """Return an <a> link to our next hop ip.
        """
        ip = self.getNextHopIp()
        if not ip: return ""
        href = self.getDmdRoot("Networks").ipHref(ip)
        if not href: return ip
        return "<a href='%s'>%s</a>" % (href, ip)

        
    security.declareProtected('View', 'getNextHopIp')
    def getNextHopIp(self):
        """Return our next hop ip (as string) if stored as object or locally.
        """
        ip = self._nexthop
        ipobj = self.nexthop()
        if ipobj: ip = ipobj.id
        return ip
 

    def getNextHopDevice(self):
        """Return the device to which this route points.
        """
        ipobj = self.nexthop()
        if ipobj: return ipobj.device()
        
    
    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """Return the interface name for this route as a string.
        If no interface is found return 'No Interface'.
        """
        if self.interface():
            return self.interface().name()
        return "No Interface"

       
    security.declareProtected('Change Device', 'setNextHopIp')
    def setNextHopIp(self, nextHopIp):
        """if the nexthop is a 127. or 0. address store locally
        else link to it in the network hierarchy"""
        if localIpCheck(self, nextHopIp) or not nextHopIp:
            self._nexthop = nextHopIp
        else:
            ip = findIpAddress(self, nextHopIp)
            if not ip: 
                netmask = 24
                int = self.interface()
                if int: 
                    intip = int.getIpAddressObj()
                    if intip: netmask = intip.netmask
                ip = self.getDmdRoot("Networks").createIp(nextHopIp, netmask)
            self.addRelation('nexthop', ip)
      

    def matchTarget(self, ip):
        """Does this route target match the ip passed.
        """
        if self.target(): return self.target().hasIp(ip)      
            
    
    def setTarget(self, netip):
        """Set this route target netip in the form 10.0.0.0/24.
        """
        if localIpCheck(self, netip):
            self._target = netip
        else:
            net = self.getDmdRoot("Networks").createNet(netip)
            self.target.addRelation(net)


    def getTarget(self):
        """Return the route target ie 0.0.0.0/0.
        """
        if self.target(): 
            return self.target().getNetworkName()
        else:
            return self._target


    def getTargetIp(self):
        """Return the target network Ip ie: 10.2.1.0
        """
        return self.getTarget().split("/")[0]

        
    def getTargetLink(self):
        """Return an <a> link to our target network.
        """
        if self.target(): 
            return self.target.getPrimaryLink()
        else:
            return self._target


    security.declareProtected('Change Device', 'setInterfaceIndex')
    def setInterfaceIndex(self, ifindex):
        for int in self.os().interfaces():
            if int.ifindex == ifindex: break
        else:
            int = None
        if int: self.interface.addRelation(int)
        else: log.warn("interface index:%s not found", ifindex)


    def getInterfaceIndex(self):
        int = self.interface()
        if int: return int.ifindex


    security.declareProtected('Change Device', 'setInterfaceName')
    def setInterfaceName(self, intname):
        int = self.os().interfaces._getOb(intname,None)
        if int: self.interface.addRelation(int)
        else: log.warn("interface '%s' not found", intname)


    def getInterfaceIp(self):
        int = self.interface()
        if int: return int.getIp()
        return ""


    def getInterfaceLink(self):
        """Return a link to the interface"""
        if self.interface(): return self.interface().getPrimaryUrlPath()
        else: return ""


InitializeClass(IpRouteEntry)
