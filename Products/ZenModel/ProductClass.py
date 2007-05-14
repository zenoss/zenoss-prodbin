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

__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *

class ProductClass(ZenModelRM, ZenPackable):


    meta_type = "ProductClass"

    #itclass = ""
    name = ""
    productKeys = []

    default_catalog = "productSearch"

    _properties = (
        #{'id':'itclass', 'type':'string', 'mode':'w'},
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'productKeys', 'type':'lines', 'mode':'w'},
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("instances", ToMany(ToOne, "Products.ZenModel.MEProduct", "productClass")),
        ("manufacturer", ToOne(ToManyCont,"Products.ZenModel.Manufacturer","products")),
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
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )
    
    security = ClassSecurityInfo()
    

    def __init__(self, id, title="", prodName=None,
                 productKey=None, partNumber="",description=""):
        ZenModelRM.__init__(self, id, title)
        # XXX per a comment in #406 from Erik, we may want to get rid
        # of prodName and only use productKey, to avoid redundancy
        if productKey:
            self.productKeys = [productKey]
        elif prodName:
            self.productKeys = [prodName]
        else:
            # When adding manually through the gui both prodName and 
            # productKey will be None
            self.productKeys = []
        if prodName is None:  self.name = id
        else: self.name = prodName
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


    def getProductKey(self):
        """Return the first product key of the device.
        """
        if len(self.productKeys) > 0:
            return self.productKeys[0]
        return ""


    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        super(ProductClass,self).manage_afterAdd(item, container)
        self.index_object()


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        super(ProductClass,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(ProductClass,self).manage_beforeDelete(item, container)
        self.unindex_object()


    security.declareProtected('Manage DMD', 'manage_editProductClass')
    def manage_editProductClass(self, name="", productKeys=[], isOS=False,
                               partNumber="", description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        redirect = self.rename(name)
        productKeys = [ l.strip() for l in productKeys.split('\n') ]
        if productKeys != self.productKeys:
            self.unindex_object()
            self.productKeys = productKeys
            self.index_object()
        self.partNumber = partNumber
        self.description = description
        self.isOS = isOS
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
            return self.callZenScreen(REQUEST, redirect)
   

InitializeClass(ProductClass)
