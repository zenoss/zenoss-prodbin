#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""IpNetwork

IpNetwork represents an IP network which contains
many IP addresses.

$Id: IpNetwork.py,v 1.22 2004/04/12 16:21:25 edahl Exp $"""

__version__ = "$Revision: 1.22 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.CMFCore import permissions

from Products.ZenUtils.IpUtil import checkip, maskToBits, numbip, getnetstr

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams
from IpAddress import manage_addIpAddress
from DeviceOrganizer import DeviceOrganizer

def manage_addIpNetwork(context, id, netmask=24, REQUEST = None):
    """make a IpNetwork"""
    d = IpNetwork(id, netmask=netmask)
    context._setObject(d.id, d)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addIpNetwork = DTMLFile('dtml/addIpNetwork',globals())

# when an ip is added the defaul location will be
# into class A->B->C network tree
defaultNetworkTree = (8,16,24)

def addIpAddressToNetworks(context, ip, netmask=24):
    """place the ip in a hierarchy of subnetworks based on the
    variable defaultNetworkTree (or zDefaulNetworkTree)"""
    netobj = context.getDmdRoot("Networks")
    netTree = getattr(netobj, 'zDefaultNetworkTree', defaultNetworkTree)
    for treemask in netTree:
        if treemask > netmask:
            break
        else:
            netip = getnetstr(ip, treemask)
            nextnet = netobj.getSubNetwork(netip)
            if nextnet:
                netobj = nextnet
            else:
                netobj = netobj.addSubNetwork(netip, treemask)
    ipobj = netobj.addIpAddress(ip,netmask)
    return ipobj


class IpNetwork(DeviceOrganizer):
    """IpNetwork object"""
    
    # Organizer configuration
    dmdRootName = "Networks"

    # Index name for IP addresses
    class_default_catalog = 'ipSearch'

    portal_type = meta_type = 'IpNetwork'

    _properties = (
                    {'id':'netmask', 'type':'string', 'mode':'w'},
                    {'id':'description', 'type':'text', 'mode':'w'},
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
                  permissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
          },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, netmask=24, description=''):
        DeviceOrganizer.__init__(self, id, description)
        if id != "Networks": 
            checkip(id)
        self.netmask = maskToBits(netmask)
        self.description = description


    def getNetworkName(self):
        """return the full network name of this network"""
        return "%s/%d" % (self.id, self.netmask)


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """make sure that networks sort correctly"""
        return numbip(self.id)


    security.declareProtected('Change Network', 'addSubNetwork')
    def addSubNetwork(self, ip, netmask=24):
        """add subnetwork to this network and return it"""
        manage_addIpNetwork(self.children,ip,netmask)
        return self.getSubNetwork(ip)


    security.declareProtected('View', 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self.children._getOb(ip, None)

    
    security.declareProtected('Change Network', 'addIpAddress')
    def addIpAddress(self, ip, netmask=24):
        """add ip to this network and return it"""
        manage_addIpAddress(self.ipaddresses,ip,netmask)
        return self.getIpAddress(ip)


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self, ip):
        """get an ip on this network"""
        return self.ipaddresses._getOb(ip, None)


    security.declareProtected('View', 'countIpAddresses')
    def countIpAddresses(self, inuse=False):
        """get an ip on this network"""
        if inuse:
            count = len(filter(lambda x: x.getDevice(), self.ipaddresses()))
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
        """aggrigate ping status for all devices in this group and below"""
        return DeviceOrganizer.pingStatus(self, "ipaddresses")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceOrganizer.snmpStatus(self, "ipaddresses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "ipaddresses")


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.class_default_catalog, 
                            self.class_default_catalog)
        zcat = self._getOb(self.class_default_catalog)
        makeConfmonLexicon(zcat)
        zcat.addIndex('id', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('id'))
        zcat.addColumn('getPrimaryUrlPath')
    
     
InitializeClass(IpNetwork)
