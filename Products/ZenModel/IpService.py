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

__doc__="""IpService.py

IpService is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: IpService.py,v 1.10 2004/04/22 22:04:14 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from Products.ZenRelations.RelSchema import *

from Service import Service
from Products.ZenModel.IpServiceClass import IpServiceClass

def manage_addIpService(context, id, protocol, port, userCreated=None, REQUEST=None):
    """make a device"""
    s = IpService(id)
    context._setObject(id, s)
    s = context._getOb(id)
    #setattr(s, 'name', id)
    setattr(s, 'protocol', protocol)
    setattr(s, 'port', int(port))
    args = {'protocol':protocol, 'port':int(port)}
    s.setServiceClass(args)
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpService = DTMLFile('dtml/addIpService',globals())


def getIpServiceKey(protocol, port):
    return "%s_%05d" % (protocol, port)


class IpService(Service):
    """
    IpService object
    """

    portal_type = meta_type = 'IpService'

    protocols = ('tcp', 'udp')

    ipaddresses = []
    discoveryAgent = ""
    port = 0 
    protocol = ""

    _properties = (
        {'id':'port', 'type':'int', 'mode':'', 'setter': 'setPort'},
        {'id':'protocol', 'type':'string', 'mode':'', 'setter': 'setProtocol'},
        {'id':'ipaddresses', 'type':'lines', 'mode':''},
        {'id':'discoveryAgent', 'type':'string', 'mode':''},
        ) 
    _relations = Service._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","ipservices")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'ipServiceDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceDetail'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'ipServiceManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def monitored(self):
        """Return monitored state of ipservice.  
        If service only listens on 127.0.0.1 return false.
        """
        if self.cantMonitor(): return False
        return super(IpService, self).monitored()
        

    def cantMonitor(self):
        """Return true if IpService only listens on 127.0.0.1.
        """
        return len(self.ipaddresses) == 1 and "127.0.0.1" in self.ipaddresses


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "%s-%d ips:%s" % (self.protocol, self.port, 
                                 ", ".join(self.ipaddresses))

        
    def setServiceClass(self, kwargs):
        """Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        protocol = kwargs['protocol']
        port = kwargs['port']
        name = getIpServiceKey(protocol, port)
        path = "/IpService/"
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, path=path, 
                               factory=IpServiceClass, port=port)
        self.serviceclass.addRelation(srvclass)


    def getSendString(self):
        return self.getAqProperty("sendString")


    def getExpectRegex(self):
        return self.getAqProperty("expectRegex")


    def getServiceClass(self):
        """Return a dict like one set by IpServiceMap for services.
        """
        svc = self.serviceclass()
        if svc:
            return {'protocol': self.protocol, 'port': svc.port }
        return {}


    def primarySortKey(self):
        return "%s-%05d" % (self.protocol, self.port)
    
    def getProtocol(self):
        return self.protocol

    def getPort(self):
        return self.port
        
    def getKeyword(self):
        sc = self.serviceclass()
        if sc: return sc.name

    def getDescription(self):
        sc = self.serviceclass()
        if sc: return sc.description

    def ipServiceClassUrl(self):
        sc = self.serviceclass()
        if sc: return sc.getPrimaryUrlPath()
    
    
    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, id=None, 
                        status=None, ipaddresses=None, 
                        protocol=None, port=None,
                        description=None, 
                        monitor=False, severity=5, sendString="",
                        expectRegex="", REQUEST=None):
        """Edit a Service from a web page.
        """
        if id:
            self.rename(id)
            if status: self.status = status
            self.ipaddresses = ipaddresses
            self.description = description
            self.protocol = protocol
            self.port = int(port)
            if protocol != self.protocol or port != self.port:
                self.setServiceClass({'protocol':protocol, 'port':int(port)})
        
        msg = []
        msg.append(self.setAqProperty("sendString", sendString, "string"))
        msg.append(self.setAqProperty("expectRegex", expectRegex, "string"))
        self.index_object()
        
        return super(IpService, self).manage_editService(monitor, severity, 
                                        msg=msg,REQUEST=REQUEST)


InitializeClass(IpService)
