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

__doc__="""IpNetwork

IpNetwork represents an IP network which contains
many IP addresses.

$Id: IpNetwork.py,v 1.22 2004/04/12 16:21:25 edahl Exp $"""

__version__ = "$Revision: 1.22 $"[11:-2]

import os
import sys
import math
import transaction
import logging
log = logging.getLogger('zen')

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions


from Products.ZenUtils.IpUtil import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

from IpAddress import IpAddress
from DeviceOrganizer import DeviceOrganizer

from Products.ZenModel.Exceptions import *

from Products.ZenUtils.Utils import setWebLoggingStream, clearWebLoggingStream

def manage_addIpNetwork(context, id, netmask=24, REQUEST = None):
    """make a IpNetwork"""
    net = IpNetwork(id, netmask=netmask)
    context._setObject(net.id, net)
    if id == "Networks":
        net = context._getOb(net.id)
        net.buildZProperties()
        net.createCatalog()
        #manage_addZDeviceDiscoverer(context)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addIpNetwork = DTMLFile('dtml/addIpNetwork',globals())


# when an ip is added the defaul location will be
# into class A->B->C network tree
defaultNetworkTree = (32,)

class IpNetwork(DeviceOrganizer):
    """IpNetwork object"""
    
    isInTree = True
    
    # Organizer configuration
    dmdRootName = "Networks"

    # Index name for IP addresses
    default_catalog = 'ipSearch'

    portal_type = meta_type = 'IpNetwork'

    _properties = (
        {'id':'netmask', 'type':'int', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        )
    
    _relations = DeviceOrganizer._relations + (
        ("ipaddresses", ToManyCont(ToOne, "Products.ZenModel.IpAddress", "network")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","target")),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "networks")),
        )
                   
    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'IpNetwork',
            'meta_type'      : 'IpNetwork',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpNetwork_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpNetwork',
            'immediate_view' : 'viewNetworkOverview',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewNetworkOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, netmask=24, description=''):
        if id.find("/") > -1: id, netmask = id.split("/",1)
        DeviceOrganizer.__init__(self, id, description)
        if id != "Networks":
            checkip(id)
        self.netmask = maskToBits(netmask)
        self.description = description


    def createNet(self, netip, netmask=0):
        """Return and create if nessesary netip.  netip in form 1.1.1.0/24 or
        with netmask passed as parameter.
        Subnetworks created based on the zParameter zDefaulNetworkTree.
        """
        netroot = self.getDmdRoot("Networks")
        if netip.find("/") > -1:
            netip, netmask = netip.split("/",1)
            netmask = int(netmask)
        netobj = netroot.getNet(netip)
        if netobj: return netobj
        if netmask == 0:
            raise ValueError("netip '%s' without netmask", netip)
        netip = getnetstr(netip,netmask)
        netTree = getattr(netroot, 'zDefaultNetworkTree', defaultNetworkTree)
        netTree = map(int, netTree)
        netobj = netroot
        for treemask in netTree:
            if treemask >= netmask:
                netobj = netobj.addSubNetwork(netip, netmask)
                break
            else:
                supnetip = getnetstr(netip, treemask)
                netobj = netobj.addSubNetwork(supnetip, treemask)
        return netobj
       

    def getNet(self, ip):
        """Return the net starting form the Networks root for ip.
        """
        return self.getDmdRoot("Networks")._getNet(ip)


    def _getNet(self, ip):
        """Recurse down the network tree to find the net of ip.
        """
        for net in self.children():
            if net.hasIp(ip):
                if len(net.children()):
                    return net._getNet(ip)
                else:
                    return net


    def createIp(self, ip, netmask=24):
        """Return an ip and create if nessesary in a hierarchy of 
        subnetworks based on the zParameter zDefaulNetworkTree.
        """
        netobj = self.getDmdRoot("Networks")
        ipobj = self.findIp(ip)
        if ipobj: return ipobj
        ipobj = netobj.addIp(ip)
        if ipobj: return ipobj
        netobj = self.createNet(ip, netmask)
        ipobj = netobj.addIpAddress(ip,netmask)
        return ipobj


    def addIp(self, ip):
        """Add an ip to the system.  Its network object must already exist.
        """
        for net in self.children():
            if net.hasIp(ip):
                if not len(net.children()):
                    return net.addIpAddress(ip, net.netmask)
                else:
                    return net.addIp(ip)
        return None


    def freeIps(self):
        """Number of free Ips left in this network.
        """
        return int(math.pow(2,32-self.netmask)-(self.countIpAddresses()+2))


    def hasIp(self, ip):
        """Does network have (contain) this ip.
        """
        start = numbip(self.id)
        end = start + math.pow(2,32-self.netmask)
        return start <= numbip(ip) < end

        
    def fullIpList(self):
        """Return a list of all ips in this network.
        """
        ipnumb = numbip(self.id)
        maxip = math.pow(2,32-self.netmask)
        start = int(ipnumb+1)
        end = int(ipnumb+maxip-1)
        return map(strip, range(start,end))
        

    def deleteUnusedIps(self):
        """Delete ips that are unused in this network.
        """
        for ip in self.ipaddresses():
            if ip.device(): continue
            self.ipaddresses.removeRelation(ip)


    def defaultRouterIp(self):
        """Return the ip of the default router for this network.
        It is based on zDefaultRouterNumber which specifies the sequence
        number that locates the router in this network.  If:
        zDefaultRouterNumber==1 for 10.2.1.0/24 -> 10.2.1.1
        zDefaultRouterNumber==254 for 10.2.1.0/24 -> 10.2.1.254
        zDefaultRouterNumber==1 for 10.2.2.128/25 -> 10.2.2.129
        zDefaultRouterNumber==126 for 10.2.2.128/25 -> 10.2.2.254
        """
        roffset = getattr(self, "zDefaultRouterNumber", 1)
        return strip((numbip(self.id) + roffset))


    def getNetworkName(self):
        """return the full network name of this network"""
        return "%s/%d" % (self.id, self.netmask)


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """make sure that networks sort correctly"""
        return numbip(self.id)


    security.declareProtected('Change Network', 'addSubNetwork')
    def addSubNetwork(self, ip, netmask=24):
        """Return and add if nessesary subnetwork to this network.
        """
        netobj = self.getSubNetwork(ip)
        if not netobj:
            net = IpNetwork(ip, netmask)
            self._setObject(ip, net)
        return self.getSubNetwork(ip)


    security.declareProtected('View', 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self._getOb(ip, None)

    
    def getSubNetworks(self):
        """Return all network objects below this one.
        """
        nets = self.children()
        for subgroup in self.children():
            nets.extend(subgroup.getSubNetworks())
        return nets


    security.declareProtected('Change Network', 'addIpAddress')
    def addIpAddress(self, ip, netmask=24):
        """add ip to this network and return it"""
        ipobj = IpAddress(ip,netmask)
        self.ipaddresses._setObject(ip, ipobj)
        return self.getIpAddress(ip)


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self, ip):
        """get an ip on this network"""
        return self.ipaddresses._getOb(ip, None)

    security.declareProtected('Change Network', 'manage_deleteIpAddresses')
    def manage_deleteIpAddresses(self, ipaddresses=(), REQUEST=None):
        """Delete ipaddresses by id from this network.
        """
        for ipaddress in ipaddresses:  
            ip = self.getIpAddress(ipaddress)
            self.ipaddresses.removeRelation(ip)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected('View', 'countIpAddresses')
    def countIpAddresses(self, inuse=True):
        """get an ip on this network"""
        if inuse:
            count = len(filter(lambda x: x.getStatus() == 0, self.ipaddresses()))
        else:
            count = self.ipaddresses.countObjects()
        for net in self.children():
            count += net.countIpAddresses(inuse)
        return count

    security.declareProtected('View', 'countDevices')
    countDevices = countIpAddresses
   

    def getAllCounts(self):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        counts = [
            self.ipaddresses.countObjects(),
            self._status("Ping", "ipaddresses"),
            self._status("Snmp", "ipaddresses"),
        ]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts

    
    def pingStatus(self):
        """aggregate ping status for all devices in this group and below"""
        return DeviceOrganizer.pingStatus(self, "ipaddresses")

    
    def snmpStatus(self):
        """aggregate snmp status for all devices in this group and below"""
        return DeviceOrganizer.snmpStatus(self, "ipaddresses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "ipaddresses")


    def findIp(self, ip):
        """Find an ipAddress.
        """
        searchCatalog = self.getDmdRoot("Networks").ipSearch
        ret = searchCatalog({'id':ip})
        if not ret: return None
        if len(ret) > 1:
            raise IpAddressConflict, "IP address conflict for IP: %s" % ip
        try:
            return self.getObjByPath(ret[0].getPrimaryId)
        except KeyError:
            log.warn("bad path '%s' in index ipSearch" % ret[0].getPrimaryId)


    def ipHref(self,ip):
        """Return the url of an ip address.
        """
        ip = self.findIp(ip)
        if ip:
            return ip.getPrimaryUrlPath()
        return ""


    def buildZProperties(self):
        nets = self.getDmdRoot("Networks")
        if getattr(aq_base(nets), "zDefaultNetworkTree", False):
            return
        nets._setProperty("zDefaultNetworkTree", (24,32), type="lines")
        nets._setProperty("zAutoDiscover", True, type="boolean")
        nets._setProperty("zPingFailThresh", 168, type="int")
                          


    def reIndex(self):
        """Go through all ips in this tree and reindex them."""
        zcat = self._getCatalog()
        zcat.manage_catalogClear()
        transaction.savepoint()
        for net in self.getSubNetworks():
            for ip in net.ipaddresses():
                ip.index_object()
            transaction.savepoint()


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX convert to ManagableIndex
        manage_addZCatalog(self, self.default_catalog,
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('id', makeCaseInsensitiveFieldIndex('id'))
        zcat.addColumn('getPrimaryId')


    def discoverDevices(self, organizerPaths=None, REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration. 
        """      
        if not organizerPaths: return self.callZenScreen(REQUEST)
        
        if REQUEST:
            response = REQUEST.RESPONSE
            dlh = self.discoverLoggingHeader()
            idx = dlh.rindex("</table>")
            dlh = dlh[:idx]
            idx = dlh.rindex("</table>")
            dlh = dlh[:idx]
            response.write(str(dlh[:idx]))
            handler = setWebLoggingStream(response)
        
        orgroot = self.getDmdRoot(self.dmdRootName)
        from popen2 import Popen4
        for organizerName in organizerPaths:
            try:
                organizer = orgroot.getOrganizer(organizerName)
                zendiscCmd = "zendisc run --net=%s" % organizer.id
                log.info('Executing command: %s' % zendiscCmd)
                f = Popen4(zendiscCmd)
                while 1:
                    s = f.fromchild.readline()
                    if not s: break
                    else: log.info(s)
            except (SystemExit, KeyboardInterrupt): raise
            except ZentinelException, e:
                log.critical(e)
            except: raise
        log.info('Done')
        
        if REQUEST:
            self.loaderFooter(response)
            clearWebLoggingStream(handler)


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        log = logging.getLogger()
        if getattr(self, "_v_handler", False):
            log.removeHandler(self._v_handler)


    def loaderFooter(self, response):
        """add navigation links to the end of the loader output"""
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to network <a href=%s>%s</a></td></tr>""" 
            % (self.absolute_url(), self.id))
        response.write("</table></body></html>")


InitializeClass(IpNetwork)
