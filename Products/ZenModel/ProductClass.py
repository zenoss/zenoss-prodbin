#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import re

from Globals import InitializeClass

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *

class ProductClass(ZenModelRM):

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    meta_type = "ProductClass"

    #itclass = ""
    name = ""

    default_catalog = "productSearch"

    _properties = (
        #{'id':'itclass', 'type':'string', 'mode':'w'},
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("instances", ToMany(ToOne, "MEProduct", "productClass")),
        ("manufacturer", ToOne(ToManyCont,"Manufacturer","products")),
    )


    def __init__(self, id, title="", productKey="", 
                partNumber="", description=""):
        if not productKey: productKey = id
        id = self.prepId.sub('_', id)
        ZenModelRM.__init__(self, id, title)
        self.productKey = productKey
        self.partNumber = partNumber
        self.description = description

    
    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        if item == self: 
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
        if item == self or getattr(item, "_operation", -1) < 1: 
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


    
InitializeClass(ProductClass)
