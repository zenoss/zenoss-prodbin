#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Hardware

Hardware represents a hardware vendor's product.

$Id: Hardware.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions
from Acquisition import aq_parent

from Products.ZenRelations.RelSchema import *

from Product import Product
from DeviceManagerBase import DeviceManagerBase


def manage_addHardware(context, id, title = None, REQUEST = None):
    """make a Hardware"""
    d = Hardware(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardware = DTMLFile('dtml/addHardware',globals())

class Hardware(Product, DeviceManagerBase):
    """Hardware object"""
    portal_type = meta_type = 'Hardware'

    _relations = Product._relations + (
        ("devices", ToMany(ToOne,"Device","model")),
        )

    factory_type_information = ( 
        { 
            'id'             : 'Hardware',
            'meta_type'      : 'Hardware',
            'description'    : """Class to manage product information""",
            'icon'           : 'Hardware_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addHardware',
            'immediate_view' : 'viewProductOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewProductOverview'
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

    def __init__(self, id, title = None, value = ''):
        Product.__init__(self, id, title)


    def moveTargets(self):
        """see IManageDevice"""
        return filter(lambda x: x != self.id, aq_parent(self).objectIds()) 
            
           
    def getMoveTarget(self, moveTargetName):
        """see IManageDevice"""
        return aq_parent(self)._getOb(moveTargetName)


InitializeClass(Hardware)
