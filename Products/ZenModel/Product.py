#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Product

Product is a base class that represents an item that can be
purchased from a vendor and integrated into the client's system.

$Id: Product.py,v 1.8 2003/03/07 15:48:57 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Instance import Instance

def manage_addProduct(context, id, title = None, REQUEST = None):
    """make a Product"""
    d = Product(id, title)
    context._setObject(id, d)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 

addProduct = DTMLFile('dtml/addProduct',globals())

    
class Product(Instance):
    """Product object"""
    portal_type = meta_type = 'Product'
    _properties = (
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 
    _relations = (
        ("manufacturer", ToOne(ToMany,"Company","products")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Product',
            'meta_type'      : 'Product',
            'description'    : """Class to manage product information""",
            'icon'           : 'Product_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addProduct',
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
    
    security = ClassSecurityInfo()

    def __init__(self, id,
        title = None,
        partNumber = '',
        description = ''):

        Instance.__init__(self, id, title)
        self.name = id
        self.partNumber = partNumber
        self.description = description

    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerLink(self, target=None):
        m = self.manufacturer()
        if m:
            return m.getPrimaryLink(target)
        return None

InitializeClass(Product)
