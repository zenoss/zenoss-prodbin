#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Hardware

Hardware represents a hardware vendor's product.

$Id: Hardware.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Product import Product

def manage_addHardware(context, id, title = None, REQUEST = None):
    """make a Hardware"""
    d = Hardware(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardware = DTMLFile('dtml/addHardware',globals())

class Hardware(Product):
    """Hardware object"""
    portal_type = meta_type = 'Hardware'

    factory_type_information = ( 
        { 
            'id'             : 'Hardware',
            'meta_type'      : 'Hardware',
            'description'    : """Class to manage product information""",
            'icon'           : 'Hardware_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addHardware',
            'immediate_view' : 'viewHardwareOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewProductOverview'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.ModifyPortalContent, )
                },
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewItem'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )

    def __init__(self, id, title = None, value = ''):
        Product.__init__(self, id, title)

InitializeClass(Hardware)
