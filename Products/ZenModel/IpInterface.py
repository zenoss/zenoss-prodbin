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

__doc__="""IpInterface

IpInterface is a collection of devices and subsystems that make
up a business function
"""

import re
import copy
import logging
log = logging.getLogger("zen.IpInterface")

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import localIpCheck, localInterfaceCheck 
from Products.ZenUtils.IpUtil import *

from ConfmonPropManager import ConfmonPropManager
from OSComponent import OSComponent
from Products.ZenModel.Exceptions import *
from Products.ZenModel.Linkable import Layer2Linkable

from Products.ZenModel.ZenossSecurity import *

def manage_addIpInterface(context, id, userCreated, REQUEST = None):
    """
    Make a device via the ZMI
    """
    d = IpInterface(id)
    context._setObject(id, d)
    d = context._getOb(id)
    d.interfaceName = id
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
        )

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","interfaces")),
        ("ipaddresses", ToMany(ToOne,"Products.ZenModel.IpAddress","interface")),
        ("iproutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","interface")),
        )

    zNoPropertiesCopy = ('ips','macaddress')
   
    localipcheck = re.compile(r'^127.|^0.').search
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
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
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


    def index_object(self):
        """
        Override the default so that links are indexed.
        """
        super(IpInterface, self).index_object()
        self.index_links()


    def unindex_object(self):
        """
        Override the default so that links are unindexed.
        """
        self.unindex_links()
        super(IpInterface, self).unindex_object()


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
        ipobj.index_links()
  

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
            return True


    def setIpAddresses(self, ips):
        """
        Set a list of ipaddresses in the form 1.1.1.1/24 on to this 
        interface. If networks for the ips don't exist they will be created.
        """
        if type(ips) == type(''): ips = [ips,]
        if self.clearIps(ips): return

        ipids = self.ipaddresses.objectIdsAll()
        localips = copy.copy(self._ipAddresses)
        for ip in ips:
            if localIpCheck(self, ip) or localInterfaceCheck(self, self.id):
                if not ip in localips:
                    self.addLocalIpAddress(ip)
                else:
                    localips.remove(ip)
            else:
                # do this funky filtering because the id we have
                # is a primary id /zport/dmd/Newtowrks... etc
                # and we are looking for just the IP part
                # we used the full id later when deleting the IPs
                rawip = ipFromIpMask(ip)
                ipmatch = filter(lambda x: x.find(rawip) > -1, ipids)
                if not ipmatch:
                    self.addIpAddress(ip)
                elif len(ipmatch) == 1:
                    ipids.remove(ipmatch[0])


        #delete ips that are no longer in use
        for ip in ipids:
            ipobj = self.ipaddresses._getOb(ip)
            self.removeRelation('ipaddresses', ipobj)
            ipobj.index_links()
        for ip in localips:
            self._ipAddresses.remove(ip)
   

    def removeIpAddress(self, ip):
        """
        Remove an ipaddress from this interface.
        """
        for ipobj in self.ipaddresses():
            if ipobj.id == ip:
                self.ipaddresses.removeRelation(ipobj)
                ipobj.index_links()
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
        Return the ipaddress as a 32bit integter for sorting purposes.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].primarySortKey()
        elif len(self._ipAddresses):
            return numbip(self._ipAddresses[0].split('/')[0])


    def getIpAddress(self):
        """
        Return the first ipaddress with its netmask ie: 1.1.1.1/24.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIpAddress()
        elif len(self._ipAddresses):
            return self._ipAddresses[0]


    def getIpAddressObj(self):
        """
        Return the first real ipaddress object or None if none are found.
        """
        if len(self.ipaddresses()):
            return self.ipaddresses()[0]


    def getIpAddressObjs(self):
        """
        Return a list of the ip objects on this interface.
        """
        retval=[]
        for ip in self.ipaddresses.objectValuesAll():
            retval.append(ip)
        for ip in self._ipAddresses:
            retval.append(ip)
        return retval


    def getIpAddresses(self):
        """
        Return list of ip addresses as strings in the form 1.1.1.1/24.
        """
        return map(str, self.getIpAddressObjs())


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
        IpInterface.  If none is found then the list will contain None.
        """
        templateName = self.getRRDTemplateName()
        default = self.getRRDTemplateByName(templateName)
        
        # If this interface supports 64bit interfaces, but no 64bit specific
        # template exists for it, fall back to the 32bit version.
        if not default and templateName.endswith("_64"):
            default = self.getRRDTemplateByName(templateName[:-3])
        
        # If no specific template exists for this type of interface default to
        # the ethernetCsmacd template.
        if not default:
            default = self.getRRDTemplateByName("ethernetCsmacd")
        
        if default:
            return [default]
        return []


    def snmpIgnore(self):
        """
        Ignore interface that are operationally down.
        """
        return self.operStatus > 1 or self.monitor == False


    def niceSpeed(self):
        """
        Return a string that expresses self.speed in reasonable units.
        """
        if not self.speed:
            return 'Unknown'
        speed = self.speed
        for unit in ('bps', 'Kbps', 'Mbps', 'Gbps'):
            if speed < 1000: break
            speed /= 1000.0
        return "%.3f%s" % (speed, unit)


    def manage_beforeDelete(self, item, container):
        """
        Unindex this interface after it is deleted.
        """
        if (item == self or item == self.device()
            or getattr(item, "_operation", -1) < 1):
            OSComponent.manage_beforeDelete(self, item, container)
    
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


InitializeClass(IpInterface)
