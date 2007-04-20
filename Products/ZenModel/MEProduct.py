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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from ManagedEntity import ManagedEntity

from Products.ZenRelations.RelSchema import *

class MEProduct(ManagedEntity):
    """
    MEProduct is a ManagedEntity that needs to track is manufacturer.
    For instance software and hardware.
    """

    _relations = ManagedEntity._relations + (
        ("productClass", ToOne(ToMany, "Products.ZenModel.ProductClass", "instances")),
    )

    security = ClassSecurityInfo()


    security.declareProtected('View', 'getProductName')
    def getProductName(self):
        productClass = self.productClass()
        if productClass: 
            return productClass.name and productClass.name or productClass.id
        return ''
    getModelName = getProductName


    security.declareProtected('View', 'getManufacturer')
    def getManufacturer(self):
        if self.productClass():
            return self.productClass().manufacturer()
  

    security.declareProtected('View', 'getManufacturerName')
    def getManufacturerName(self):
        manuf = self.getManufacturer()
        if manuf: return manuf.getId()
        return ""


    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerLink(self):
        if self.productClass():
            return self.productClass().manufacturer.getPrimaryLink()
        return ""

    
    def getProductKey(self):
        """Get the product class of this software.
        """
        pclass = self.productClass()
        if pclass: return pclass.getProductKey()
        return ""

    
    def getProductLink(self):
        return self.productClass.getPrimaryLink()


    def getProductContext(self):
        """Return list of tuples with product context for this product.
        """
        prod = self.productClass()
        if prod: 
            prodcontext = self.primaryAq()
            return prodcontext.zenPropertyItems()
        return []

InitializeClass(MEProduct)
