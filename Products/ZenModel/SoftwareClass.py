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

__doc__="""SoftwareClass

SoftwareClass represents a software vendor's product.

$Id: SoftwareClass.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ProductClass import ProductClass

def manage_addSoftwareClass(context, id, title = None, REQUEST = None):
    """make a SoftwareClass"""
    d = SoftwareClass(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSoftwareClass = DTMLFile('dtml/addSoftwareClass',globals())

class SoftwareClass(ProductClass):
    """SoftwareClass object"""
    portal_type = meta_type = 'SoftwareClass'

    build=""
    version=""

    _properties = ProductClass._properties + (
        {'id':'version', 'type':'string', 'mode':'w'},
        {'id':'build', 'type':'string', 'mode':'w'},
        )

#    factory_type_information = ( 
#        { 
#            'id'             : 'SoftwareClass',
#            'meta_type'      : 'SoftwareClass',
#            'description'    : """Class to manage product information""",
#            'icon'           : 'SoftwareClass_icon.gif',
#            'product'        : 'ZenModel',
#            'factory'        : 'manage_addSoftwareClass',
#            'immediate_view' : 'viewProductOverview',
#            'actions'        :
#            ( 
#                { 'id'            : 'overview'
#                , 'name'          : 'Overview'
#                , 'action'        : 'viewSoftwareClassOverview'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Changes'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#            )
#          },
#        )


InitializeClass(SoftwareClass)

class OSSoftwareClass(SoftwareClass):
    """OSSoftwareClass object"""
    portal_type = meta_type = 'OSSoftwareClass'

InitializeClass(OSSoftwareClass)