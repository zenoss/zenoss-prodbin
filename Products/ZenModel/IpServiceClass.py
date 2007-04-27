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

import logging

from Globals import DTMLFile
from Globals import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import Permissions
from AccessControl import ClassSecurityInfo

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
#                { 'id'            : 'manage'
#                , 'name'          : 'Manage'
#                , 'action'        : 'ipServiceClassManage'
#                , 'permissions'   : ("Manage DMD",)
#                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Changes'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (
#                  Permissions.view, )
#                },
            )
         },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, serviceKeys=(), description="", port=0):
        ServiceClass.__init__(self, id, serviceKeys, description)
        self.port = port


    security.declareProtected('Manage DMD', 'manage_editServiceClass')
    def manage_editServiceClass(self, name="", monitor=False, serviceKeys="",
                               port=0, description="", sendString="",
                               expectRegex="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        self.sendString = sendString
        self.expectRegex = expectRegex
        return super(IpServiceClass,self).manage_editServiceClass(
                                name, monitor, serviceKeys,
                                port, description, REQUEST=REQUEST)
   


InitializeClass(IpServiceClass)
