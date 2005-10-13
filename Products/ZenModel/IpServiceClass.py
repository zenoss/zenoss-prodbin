#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Service.py

Service is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: IpServiceClass.py,v 1.9 2004/04/07 19:55:01 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import logging

from Globals import DTMLFile
from Globals import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ServiceClass import ServiceClass
from ZenModelRM import ZenModelRM


def manage_addIpServiceClass(context, protocol, port, keyword='',
                             description='', contact='', REQUEST = None):
    """make a device"""
    id = getIpServiceClassId(protocol, port)
    ipsc = IpServiceClass(id, protocol=protocol, port=port, keyword=keyword, 
                description=description, contact=contact)
    context._setObject(ipsc.id, ipsc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 
    return ipsc.id


def addIpServiceToClass(ipservice):
    """connect an ip service instance to its class
    make the class if it doesn't exist"""
    serviceclass = ipservice.ipserviceclass()
    port = ipservice.getPort()
    proto = ipservice.getProtocol()
    if (not serviceclass 
        or port != serviceclass.port
        or proto != serviceclass.protocol):
        if port <= 1024:
            try:
                classbase = ipservice.Services.IpServices.Privileged #aq
            except AttributeError:
                logging.warn("Priviledged ports not loaded")
                return
        else:
            classbase = ipservice.Services.IpServices #aq
        id = ipservice.getIpServiceKey()
        serviceclass = classbase._getOb(id,None)
        if not serviceclass:
            manage_addIpServiceClass(classbase, proto, port)
            serviceclass = classbase._getOb(id)
        serviceclass.addRelation('ipservices', ipservice)


def getIpServiceClassId(protocol, port):
    return "%s-%05d" % (protocol, port)


addIpServiceClass = DTMLFile('dtml/addIpServiceClass',globals())

class IpServiceClass(ServiceClass, ZenModelRM):
    """Service object"""
    portal_type = meta_type = 'IpServiceClass'
    isInTree = 0 # don't want these guys in left tree
    manage_options = ZenModelRM.manage_options #FIXME
    protocols = ('tcp', 'udp')

    #view = PageTemplateFile('zpt/viewServiceOverview.zpt',globals())

    _properties = (
        {'id':'keyword', 'type':'string', 'mode':'w'},
        {'id':'port', 'type':'int', 'mode':'w'},
        {'id':'protocol', 'type':'selection', 'mode':'w',
            'select_variable':'protocols'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'contact', 'type':'string', 'mode':'w'},
        ) 
    _relations = ServiceClass._relations + (
        ("ipservices", ToManyCont(ToOne, "IpService", "ipserviceclass")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'IpServiceClass',
            'meta_type'      : 'IpServiceClass',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpServiceClass_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpServiceClass',
            'immediate_view' : 'viewIpServiceClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewIpServiceClassOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )


    def __init__(self, id, protocol='', port=0, keyword = '',
                    description = '', contact = ''):
        ServiceClass.__init__(self, id)
        self.keyword = keyword
        self.port = port
        self.protocol = protocol
        self.description = description
        self.contact = contact

    def getKeyword(self):
        if self.keyword: return self.keyword
        else: return self.id

InitializeClass(IpServiceClass)
