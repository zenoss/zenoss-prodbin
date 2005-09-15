#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""IpAddress

IpAddress represents a device residing on an IP network.

$Id: IpAddress.py,v 1.42 2004/04/15 00:54:14 edahl Exp $"""

__version__ = "$Revision: 1.42 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.FindSupport import FindSupport
from Acquisition import aq_parent    

from Products.ZenUtils.IpUtil import *
from Products.ZenUtils.Utils import getObjByPath

from DeviceResultInt import DeviceResultInt
from PingStatusInt import PingStatusInt
from Instance import Instance
from Products.ZenModel.Exceptions import * 

def manage_addIpAddress(context, id, netmask=24, REQUEST = None):
    """make a IpAddress"""
    ip = IpAddress(id, netmask)
    context._setObject(ip.id, ip)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


def findIpAddress(context, ip):
    """find an ip from base. base should be Networks root found through aq"""
    searchCatalog = context.Networks.ipSearch
    ret = searchCatalog({'id':ip})
    if len(ret) > 1: 
        raise IpAddressConflict, "IP address conflict for IP: %s" % ip
    if ret:
        ipobj = getObjByPath(searchCatalog.getPhysicalRoot(), 
                            ret[0].getPrimaryUrlPath) 
        return ipobj


addIpAddress = DTMLFile('dtml/addIpAddress',globals())


class IpAddress(Instance, PingStatusInt, DeviceResultInt):
    """IpAddress object"""
    portal_type = meta_type = 'IpAddress'

    default_catalog = 'ipSearch'

    _properties = (
                 {'id':'netmask', 'type':'string', 
                    'mode':'w', 'setter':'setNetmask'},
                 {'id':'reverseName', 'type':'string', 'mode':'w'},
                 )

    factory_type_information = ( 
        { 
            'id'             : 'IpAddress',
            'meta_type'      : 'IpAddress',
            'description'    : """Ip Address Class""",
            'icon'           : 'IpAddress_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpAddress',
            'immediate_view' : 'viewIpAddressOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewIpAddressOverview'
                , 'permissions'   : ( "View", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, netmask=24):
        checkip(id)
        Instance.__init__(self, id)
        self._pingStatus = None
        self._netmask = maskToBits(netmask)
        self.reverseName = ""


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """make sure that networks sort correctly"""
        return numbip(self.id)


    def setNetmask(self, value):
        self._netmask = maskToBits(value)


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'netmask':
            self.setNetmask(value)
        else:    
            setattr(self,id,value)


    def __getattr__(self, name):
        if name == 'device':
            return self.getDevice()
        elif name == 'deviceName':
            d = self.getDevice()
            if d:
                return d.id
            return None
        elif name == 'netmask':
            return self._netmask
        else:
            raise AttributeError, name


    security.declareProtected('Change Device', 'setIpAddress')
    def setIpAddress(self, ip):
        """set the ipaddress can be in the form 1.1.1.1/24 to also set mask"""
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            self._netmask = maskToBits(iparray[1])
        checkip(ip)
        aqself = self.aq_primary() #set aq path
        network = aqself.aq_parent
        netip = getnetstr(ip, network.netmask)
        if netip == network.id:
            aqs.aq_parent._renameObject(aqs.id, ip)
        else:
            raise WrongSubNetError, \
                    "Ip %s is in a different subnet than %s" % (ip, self.id)
                    


    security.declareProtected('View', 'getIp')
    def getIp(self):
        """return only the ip"""
        return self.id


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self):
        """return the ip with its netmask in the form 1.1.1.1/24"""
        return self.id + "/" + str(self._netmask)


    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        if self.interface():
            return self.interface().name
        return "No Interface"


    security.declareProtected('View', 'getNetworkName')
    def getNetworkName(self):
        if self.network():
            return self.network().getNetworkName()
        return "No Network"


    security.declareProtected('View', 'getNetworkUrl')
    def getNetworkUrl(self):
        if self.network():
            return self.network().absolute_url()
        return ""


    def getDevice(self):
        """get the device for this ip for DeviceResultInt"""
        if self.interface():
            return self.interface().device()
        return None


    def trackStatus(self, off=0):
        """manage tracking ping status on this ip address"""
        if off:
            self._pingStatus = None
        else:
            self._pingStatus = ZenStatus(-1)


    def _getPingStatusObj(self):
        """get the ping status object for this IpAddress
        if there is no _pingStatus attribute use the device status"""
        if self._pingStatus == None:
            d = self.getDevice()
            if d: return d._getPingStatusObj()


InitializeClass(IpAddress)
