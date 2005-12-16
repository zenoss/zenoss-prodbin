#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Manufacturer

Manufacturer is a base class that represents a vendor of Products.

$Id: Manufacturer.py,v 1.11 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from Globals import DTMLFile, InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM

def manage_addManufacturer(context, id, REQUEST = None):
    """make a Manufacturer"""
    d = Manufacturer(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addManufacturer = DTMLFile('dtml/addManufacturer',globals())

class Manufacturer(ZenModelRM):
    """Manufacturer object"""
    portal_type = meta_type = 'Manufacturer'

    url = ''
    supportNumber = ''
    address1 = ''
    address2 = ''
    city = ''
    state = ''
    zip = ''

    _properties = (
        {'id':'url', 'type':'string', 'mode':'w'},
        {'id':'supportNumber', 'type':'string', 'mode':'w'},
        {'id':'address1', 'type':'string', 'mode':'w'},
        {'id':'address2', 'type':'string', 'mode':'w'},
        {'id':'city', 'type':'string', 'mode':'w'},
        {'id':'state', 'type':'string', 'mode':'w'},
        {'id':'zip', 'type':'string', 'mode':'w'},
        )

    _relations = (
        ("products", ToManyCont(ToOne,"ProductClass","manufacturer")),
    )
 
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Manufacturer',
            'meta_type'      : 'Manufacturer',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Manufacturer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addManufacturer',
            'immediate_view' : 'viewManufacturerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturerOverview'
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


    def getProductNames(self):
        """return a list of all products this Manufacturer makes"""
        prods = [""]
        prods.extend(map(lambda x: x.getId(),
                Manufacturer.products.objectValuesAll()))
        prods.sort()
        return prods



InitializeClass(Manufacturer)
