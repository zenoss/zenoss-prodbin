#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import re

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *

class ProductClass(ZenModelRM):

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    meta_type = "ProductClass"

    #itclass = ""
    name = ""
    productKey = ""

    default_catalog = "productSearch"

    _properties = (
        #{'id':'itclass', 'type':'string', 'mode':'w'},
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'productKey', 'type':'string', 'mode':'w'},
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("instances", ToMany(ToOne, "MEProduct", "productClass")),
        ("manufacturer", ToOne(ToManyCont,"Manufacturer","products")),
    )

    factory_type_information = ( 
        { 
            'id'             : 'ProductClass',
            'meta_type'      : 'ProductClass',
            'description'    : """Class to manage product information""",
            'icon'           : 'ProductClass.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addProductClass',
            'immediate_view' : 'viewProductClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewProductClassOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editProductClass'
                , 'permissions'   : ("Manage DMD", )
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
    

    def __init__(self, id, title="", productKey="", 
                partNumber="", description=""):
        if not productKey: productKey = id
        id = self.prepId.sub('_', id)
        ZenModelRM.__init__(self, id, title)
        self.productKey = productKey
        self.partNumber = partNumber
        self.description = description


    def type(self):
        """Return the type name of this product (Hardware, Software).
        """
        return self.meta_type[:-5]


    def count(self):
        """Return the number of existing instances for this class.
        """
        return self.instances.countObjects()

    
    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        self.index_object()
        ZenModelRM.manage_afterAdd(self, item, container)


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        ZenModelRM.manage_afterClone(self, item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        ZenModelRM.manage_beforeDelete(self, item, container)
        self.unindex_object()


    def index_object(self):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.productKey)
            
                                                
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.productKey)


    security.declareProtected('Manage DMD', 'manage_editProductClass')
    def manage_editProductClass(self, name="", productKey="", partNumber="", 
                                description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        redirect = self.rename(name)
        if productKey != self.productKey:
            self.unindex_object()
            self.productKey = productKey
            self.index_object()
        self.partNumber = partNumber
        self.description = description        
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST, redirect)
   

InitializeClass(ProductClass)
