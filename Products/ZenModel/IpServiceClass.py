#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

import logging

from Globals import DTMLFile
from Globals import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *

from ServiceClass import ServiceClass
from ZenModelRM import ZenModelRM


def manage_addIpServiceClass(context, id, REQUEST = None):
    """make a device"""
    ipsc = IpServiceClass(id)
    context._setObject(ipsc.id, ipsc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 
    return ipsc.id


addIpServiceClass = DTMLFile('dtml/addIpServiceClass',globals())

class IpServiceClass(ServiceClass):
    """IpServiceClass object.
    """

    port = 0
    sendString = ""
    expectRegex = ""

    portal_type = meta_type = 'IpServiceClass'

    _properties = ServiceClass._properties + (
        {'id':'port', 'type':'int', 'mode':'w'},
        {'id':'sendString', 'type':'string', 'mode':'w'},
        {'id':'expectRegex', 'type':'string', 'mode':'w'},
        ) 

    factory_type_information = ( 
        { 
            'immediate_view' : 'ipServiceClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'ipServiceClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    def __init__(self, id, serviceKeys=(), description="", port=0):
        ServiceClass.__init__(self, id, serviceKeys, description)
        self.port = port


InitializeClass(IpServiceClass)
