#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""IpService.py

IpService is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: IpService.py,v 1.10 2004/04/22 22:04:14 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from Service import Service
from IpServiceClass import addIpServiceToClass, getIpServiceClassId
from DeviceResultInt import DeviceResultInt
#from PingStatusInt import PingStatusInt

def manage_addIpService(context, id, title = None, REQUEST = None):
    """make a device"""
    d = IpService(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpService = DTMLFile('dtml/addIpService',globals())

class IpService(Service, DeviceResultInt):
    """
    IpService object
    """

    portal_type = meta_type = 'IpService'

    protocols = ('tcp', 'udp')

    _properties = (
        {'id':'port', 'type':'int', 'mode':'', 'setter': 'setPort'},
        {'id':'protocol', 'type':'string', 'mode':'', 'setter': 'setProtocol'},
        {'id':'ipaddress', 'type':'string', 'mode':''},
        {'id':'discoveryAgent', 'type':'string', 'mode':''},
        ) 
    _relations = (
        ("server", ToOne(ToManyCont,"Device","ipservices")),
        ("ipserviceclass", ToOne(ToMany,"IpServiceClass","ipservices")),
        ("clients", ToMany(ToMany,"Device","clientofservices")),
        )


    def __init__(self, id,ipaddress = ''):
        Service.__init__(self, id)
        self.ipaddress = ipaddress
        self.discoveryAgent = ""
        self._port = 0 
        self._protocol = None


    def __getattr__(self, name):
        if name == 'port':
            return self.getPort()
        elif name == 'protocol':
            return self.getProtocol()
        else:
            raise AttributeError, name


    def setPort(self, port):
        """set the port and connect to class if protocol is also set"""
        self._port = int(port)
        if self._protocol:
            addIpServiceToClass(self)

    def setProtocol(self, protocol):
        """set the protocol and connect to class if port is also set"""
        self._protocol = protocol
        if self._port:
            addIpServiceToClass(self)
       

    def getIpServiceKey(self):
        """key format to link instance to class"""
        return getIpServiceClassId(self._protocol, self._port)

    def primarySortKey(self):
        return "%s-%s:%05d" % (self._protocol, self.ipaddress, self._port)
        
    def getPort(self):
        return self._port
        #sc = self.ipserviceclass()
        #if sc: return sc.port


    def getProtocol(self):
        return self._protocol
        #sc = self.ipserviceclass()
        #if sc: return sc.protocol


    def getDevice(self):
        return self.server()

    
    def getKeyword(self):
        sc = self.ipserviceclass()
        if sc: return sc.getKeyword()

    def getDescription(self):
        sc = self.ipserviceclass()
        if sc: return sc.description

    def ipServiceClassUrl(self):
        sc = self.ipserviceclass()
        if sc: return sc.getPrimaryUrlPath()
    
    
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks"""
        self._wrapperCheck(value)
        if id == 'port':
            self.setPort(value)
        elif id == 'protocol':
            self.setProtocol(value)
        else:    
            setattr(self,id,value)
       

InitializeClass(IpService)
