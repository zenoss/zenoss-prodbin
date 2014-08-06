##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""IpInterface

IpInterface is a collection of devices and subsystems that make
up a business function
"""

import re
import copy
import logging
from itertools import chain
log = logging.getLogger("zen.IpInterface")

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from AccessControl import ClassSecurityInfo
from zope.event import notify
from zope.container.contained import ObjectMovedEvent

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import localIpCheck, localInterfaceCheck, convToUnits
from Products.ZenUtils.IpUtil import *

from ConfmonPropManager import ConfmonPropManager
from OSComponent import OSComponent
from Products.ZenModel.Exceptions import *
from Products.ZenModel.Linkable import Layer2Linkable

from Products.ZenModel.ZenossSecurity import *
from Products.Zuul.catalog.events import IndexingEvent


_IPADDRESS_CACHE_ATTR = "_v_ipaddresses"


def manage_addIpInterface(context, newId, userCreated, REQUEST = None):
    """
    Make a device via the ZMI
    """
    d = IpInterface(newId)
    context._setObject(newId, d)
    d = context._getOb(newId)
    d.interfaceName = newId
    if userCreated: d.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')

addIpInterface = DTMLFile('dtml/addIpInterface',globals())


class IpInterface(OSComponent, Layer2Linkable):
    """
    IpInterface object
    """

    portal_type = meta_type = 'IpInterface'

    manage_editIpInterfaceForm = DTMLFile('dtml/manageEditIpInterface',
                                                        globals())

    # catalog to find interfaces that should be pinged
    # indexes are id and description
    #default_catalog = 'interfaceSearch'

    ifindex = '0'
    interfaceName = ''
    macaddress = ""
    type = ""
    description = ""
    mtu = 0
    speed = 0
    adminStatus = 0
    operStatus = 0
    duplex = 0
    _ipAddresses =  []



    _properties = OSComponent._properties + (
        {'id':'ips', 'type':'lines', 'mode':'w', 'setter':'setIpAddresses'},
        {'id':'interfaceName', 'type':'string', 'mode':'w'},
        {'id':'ifindex', 'type':'string', 'mode':'w'},
        {'id':'macaddress', 'type':'string', 'mode':'w'},
        {'id':'type', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        {'id':'mtu', 'type':'int', 'mode':'w'},
        {'id':'speed', 'type':'long', 'mode':'w'},
        {'id':'adminStatus', 'type':'int', 'mode':'w'},
        {'id':'operStatus', 'type':'int', 'mode':'w'},
        {'id':'duplex', 'type':'int', 'mode':'w'},
        )

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","interfaces")),
        ("ipaddresses", ToMany(ToOne,"Products.ZenModel.IpAddress","interface")),
        ("iproutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","interface")),
        )

    zNoPropertiesCopy = ('ips','macaddress')

    localipcheck = re.compile(r'^127.|^0.|^::1$|^fe80:').search
    localintcheck = re.compile(r'^lo0').search

    defaultIgnoreTypes = ('Other', 'softwareLoopback', 'CATV MAC Layer')

    factory_type_information = (
        {
            'id'             : 'IpInterface',
            'meta_type'      : 'IpInterface',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpInterface_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpInterface',
            'immediate_view' : 'viewIpInterface',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewIpInterface'
                , 'permissions'   : (ZEN_VIEW,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, title = None):
        """
        Init OSComponent and set _ipAddresses to an empty list.
        """
        OSComponent.__init__(self, id, title)
        self._ipAddresses = []


    def _invalidate_ipaddress_cache(self):
        setattr(self, _IPADDRESS_CACHE_ATTR, None)

    security.declareProtected('View', 'viewName')
    def viewName(self):
        """
        Use the unmagled interface name for display
        """
        return self.interfaceName.rstrip('\x00') #Bogus fix for MS names
    name = primarySortKey = viewName

    def _setPropValue(self, id, value):
        """
        Override from PerpertyManager to handle checks and ip creation
        """
        self._wrapperCheck(value)
        if id == 'ips':
            self.setIpAddresses(value)
        else:
            setattr(self,id,value)
            if id == 'macaddress':
                self.index_object()

    def index_object(self, idxs=None):
        """
        Override the default so that links are indexed.
        """
        super(IpInterface, self).index_object(idxs)
        self.index_links()
        # index our ip addresses if necessary
        for ip in self.ipaddresses():
            ip.index_object()
        self._invalidate_ipaddress_cache()

        device = self.device()
        if self.macaddress and device:
            if (device.getMacAddressCache().add(self.macaddress)): 
                notify(IndexingEvent(device, idxs=('macAddresses',), update_metadata=False))

    def unindex_object(self):
        """
        Override the default so that links are unindexed.
        """
        self.unindex_links()
        super(IpInterface, self).unindex_object()
        # index our ip addresses if necessary
        for ip in self.ipaddresses():
            ip.index_object()

        device = self.device()

        if device:
            macs = device.getMacAddressCache()
            try: 
                macs.remove(self.macaddress)
                notify(IndexingEvent(self.device(), idxs=('macAddresses',), update_metadata=False))
            except KeyError:
                pass
            
    def manage_deleteComponent(self, REQUEST=None):
        """
        Reindexes all the ip addresses on this interface
        after it has been deleted
        """
        ips = self.ipaddresses()
        super(IpInterface, self).manage_deleteComponent(REQUEST)
        for ip in ips:
            ip.primaryAq().index_object()

    def manage_editProperties(self, REQUEST):
        """
        Override from propertiyManager so we can trap errors
        """
        try:
            return ConfmonPropManager.manage_editProperties(self, REQUEST)
        except IpAddressError, e:
            return   MessageDialog(
                title = "Input Error",
                message = e.args[0],
                action = "manage_main")


    def __getattr__(self, name):
        """
        Allow access to ipAddresses via the ips attribute
        """
        if name == 'ips':
            return self.getIpAddresses()
        else:
            raise AttributeError( name )


    def _prepIp(self, ip, netmask=24):
        """
        Split ips in the format 1.1.1.1/24 into ip and netmask.
        Default netmask is 24.
        """
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            checkip(ip)
            netmask = maskToBits(iparray[1])
        return ip, netmask


    def addIpAddress(self, ip, netmask=24):
        """
        Add an ip to the ipaddresses relationship on this interface.
        """
        self._invalidate_ipaddress_cache()
        networks = self.device().getNetworkRoot()
        ip, netmask = self._prepIp(ip, netmask)
        #see if ip exists already and link it to interface
        ipobj = networks.findIp(ip)
        if ipobj:
            dev = ipobj.device()
            if dev and dev != self.device():
                log.warn("Adding IP Address %s to %s found it on device %s",
                         ip, self.getId(), dev.getId())
            self.ipaddresses.addRelation(ipobj)
        #never seen this ip make a new one in correct subnet
        else:
            ipobj = networks.createIp(ip, netmask)
            self.ipaddresses.addRelation(ipobj)
        ipobj.index_object()
        os = self.os()
        notify(ObjectMovedEvent(self, os, self.id, os, self.id))



    def addLocalIpAddress(self, ip, netmask=24):
        """
        Add a locally stored ip. Ips like 127./8 are maintained locally.
        """
        (ip, netmask) = self._prepIp(ip, netmask)
        ip = ip + '/' + str(netmask)
        if not self._ipAddresses: self._ipAddresses = []
        if not ip in self._ipAddresses:
            self._ipAddresses = self._ipAddresses + [ip,]


    def clearIps(self, ips):
        """
        If no IPs are sent remove all in the relation
        """
        if not ips:
            self.removeRelation('ipaddresses')
            self._invalidate_ipaddress_cache()
            return True


    def setIpAddresses(self, ips):
        """
        Set a list of ipaddresses in the form 1.1.1.1/24 on to this
        interface. If networks for the ips don't exist they will be created.
        """
        if isinstance(ips, basestring): ips = [ips,]
        if self.clearIps(ips): return

        ipids = self.ipaddresses.objectIdsAll()
        localips = copy.copy(self._ipAddresses)
        for ip in ips:
            if not ip:
                continue
            if localIpCheck(self, ip) or localInterfaceCheck(self, self.id):
                if not ip in localips:
                    self.addLocalIpAddress(ip)
                else:
                    localips.remove(ip)
            else:
                # do this funky filtering because the id we have
                # is a primary id /zport/dmd/Networks... etc
                # and we are looking for just the IP part
                # we used the full id later when deleting the IPs
                rawip = ipFromIpMask(ip)
                ipmatch = filter(lambda x: x.find(rawip) > -1, ipids)
                if not ipmatch:
                    try:
                        self.addIpAddress(ip)
                    except IpAddressError:
                        log.info("Ignoring invalid IP address {rawip}".format(rawip=rawip))
                elif len(ipmatch) == 1:
                    ipids.remove(ipmatch[0])


        #delete ips that are no longer in use
        for ip in ipids:
            ipobj = self.ipaddresses._getOb(ip)
            self.removeRelation('ipaddresses', ipobj)
            ipobj.index_object()
        for ip in localips:
            self._ipAddresses.remove(ip)

    def removeIpAddress(self, ip):
        """
        Remove an ipaddress from this interface.
        """
        self._invalidate_ipaddress_cache()
        for ipobj in self.ipaddresses():
            if ipobj.id == ip:
                self.ipaddresses.removeRelation(ipobj)
                ipobj.index_object()
                return


    def getIp(self):
        """
        Return the first ip for this interface in the form: 1.1.1.1.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIp()
        elif len(self._ipAddresses):
            return self._ipAddresses[0].split('/')[0]


    def getIpSortKey(self):
        """
        Return the IP address as an integter for sorting purposes.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].primarySortKey()
        elif len(self._ipAddresses):
            return numbip(self._ipAddresses[0].split('/')[0])


    def getIpAddress(self):
        """
        Return the first IP address with its netmask ie: 1.1.1.1/24.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIpAddress()
        elif len(self._ipAddresses):
            return self._ipAddresses[0]


    def getIpAddressObj(self):
        """
        Return the first real IP address object or None if none are found.
        """
        if len(self.ipaddresses()):
            return self.ipaddresses()[0]


    def getIpAddressObjsGen(self):
        return chain(self.ipaddresses.objectValuesGen(), self._ipAddresses)


    def getIpAddressObjs(self):
        """
        Return a list of the ip objects on this interface.
        """
        return list(self.getIpAddressObjsGen())


    def getIpAddresses(self):
        """
        Return list of ip addresses as strings in the form 1.1.1.1/24.

        Because this is somewhat expensive to calculate, cache the
        result on a volatile attribute. This cache will only have the
        lifespan of this instance, but many operations (e.g., indexing)
        need it multiple times.
        """
        addrs = getattr(self, _IPADDRESS_CACHE_ATTR, None)
        if addrs is None:
            addrs = map(str, self.getIpAddressObjsGen())
            setattr(self, _IPADDRESS_CACHE_ATTR, addrs)
        return addrs


    def getNetwork(self):
        """
        Return the network for the first ip on this interface.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].network()


    def getNetworkName(self):
        """
        Return the network name for the first ip on this interface.
        """
        net = self.getNetwork()
        if net: return net.getNetworkName()
        return ""


    def getNetworkLink(self):
        """
        Return the network link for the first ip on this interface.
        """
        if len(self.ipaddresses()):
            addr = self.ipaddresses.objectValuesAll()[0]
            if addr:
                if hasattr(aq_base(addr), 'network'):
                    if self.checkRemotePerm("View", addr.network):
                        return addr.network.getPrimaryLink()
                    else:
                        return addr.network.getRelatedId()
        else:
            return ""


    def getNetworkLinks(self):
        """
        Return a list of network links for each ip in this interface.
        """
        addrs = self.ipaddresses() + self._ipAddresses
        if addrs:
            links = []
            for addr in addrs:
                if hasattr(aq_base(addr), 'network'):
                    if self.checkRemotePerm('View', addr.network()):
                        links.append(addr.network.getPrimaryLink())
                    else:
                        links.append(addr.network.getRelatedId())
                else:
                    links.append("")
            return "<br/>".join(links)
        else:
            return ""


    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """
        Return the name of this interface.
        """
        if self.interfaceName: return self.interfaceName
        elif self.viewName(): return self.viewName()
        else: return "None"


    security.declareProtected('View', 'getInterfaceMacaddress')
    def getInterfaceMacaddress(self):
        """
        Return the mac address of this interface.
        """
        return self.macaddress


    def getRRDTemplateName(self):
        """
        Return the interface type as the target type name.
        """
        return self.prepId(self.type or "Unknown")


    def getRRDTemplates(self):
        """
        Return a list containing the appropriate RRDTemplate for this
        IpInterface. If none is found then the list will be empty.

        Order of preference if the interface supports 64bit counters.
            1. <type>_64
            2. ethernetCsmacd_64
            3. <type>
            4. ethernetCsmacd

        Order of preference if the interface doesn't support 64bit counters.
            1. <type>
            2. ethernetCsmacd
        """
        templateName = self.getRRDTemplateName()

        order = ['ethernetCsmacd']
        if templateName.endswith('_64'):
            order.insert(0, 'ethernetCsmacd_64')
            if templateName not in order:
                order.insert(0, templateName)
                order.insert(2, templateName[:-3])
        else:
            if templateName not in order:
                order.insert(0, templateName)

        for name in order:
            template = self.getRRDTemplateByName(name)
            if template:
                return [template]

        return []


    def snmpIgnore(self):
        """
        Ignore interface that are administratively down.
        """
        # This must be based off the modeled admin status or zenhub could
        # lock itself up while building configurations.
        return self.adminStatus > 1 or self.monitor == False


    def getAdminStatus(self):
        """
        Get the current administrative state of the interface. 
        """
        return self.adminStatus


    def getAdminStatusString(self):
        """
        Return the current administrative state of the interface converted to
        its string version.
        """
        return {1: 'Up', 2: 'Down', 3: 'Testing'}.get(
            self.getAdminStatus(), 'Unknown')


    def getOperStatus(self):
        """
        Get the current operational state of the interface.
        """
        return self.operStatus

    def getOperStatusString(self):
        """
        Return the current operational state of the interface converted to
        its string version.
        """
        return {
            1: 'Up', 2: 'Down', 3: 'Testing', 5: 'Dormant', 6: 'Not Present',
            7: 'Lower Layer Down'}.get(
                self.getOperStatus(), 'Unknown')


    def getStatus(self, statClass=None):
        """
        Return the status number for this interface.
        """
        # Unknown status if we're not monitoring the interface.
        if self.snmpIgnore():
            return -1

        return super(IpInterface, self).getStatus()


    def niceSpeed(self):
        """
        Return a string that expresses self.speed in reasonable units.
        """
        if not self.speed:
            return 'Unknown'
        return convToUnits(self.speed, divby=1000, unitstr='bps')

    def deviceId(self):
        """
        The device id, for indexing purposes.
        """
        d = self.device()
        if d: return d.getPrimaryId()
        else: return None

    def interfaceId(self):
        """
        The interface id, for indexing purposes.
        """
        return self.getPrimaryId()

    def lanId(self):
        """
        pass
        """
        return 'None'

    def niceDuplex(self):
        """
        Return a string that expresses self.duplex into human readable format.
        """

        if self.duplex == 2:
            return 'halfDuplex'
        elif self.duplex == 3:
            return 'fullDuplex'
        return 'unknown'

InitializeClass(IpInterface)

def beforeDeleteIpInterface(ob, event):
    if (event.object==ob or event.object==ob.device() or
        getattr(event.object, "_operation", -1) < 1):
        ob.unindex_object()
