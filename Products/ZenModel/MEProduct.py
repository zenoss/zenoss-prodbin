#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

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
        ("productClass", ToOne(ToMany, "ProductClass", "instances")),
    )

    security = ClassSecurityInfo()


    security.declareProtected('View', 'getProductName')
    def getProductName(self):
        productClass = self.productClass()
        if productClass: return productClass.getId()
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
        if pclass: return pclass.productKey
        return ""

    
    def getProductLink(self):
        return self.productClass.getPrimaryLink()




InitializeClass(MEProduct)
