##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from ManagedEntity import ManagedEntity

from Products.ZenRelations.RelSchema import *

class MEProduct(ManagedEntity):
    """
    MEProduct is a ManagedEntity that needs to track is manufacturer.
    For instance software and hardware.
    """

    _prodKey = None
    _manufacturer = None

    _relations = ManagedEntity._relations + (
        ("productClass", ToOne(ToMany, "Products.ZenModel.ProductClass", "instances")),
    )

    security = ClassSecurityInfo()


    security.declareProtected('View', 'getProductName')
    def getProductName(self):
        """
        Gets the Products's Name (id)
        """
        productClass = self.productClass()
        if productClass:
            return productClass.titleOrId()
        return ''
    getModelName = getProductName


    security.declareProtected('View', 'getProductHref')
    def getProductHref(self):
        """
        Gets the Products's PrimaryHref
        """
        productClass = self.productClass()
        if productClass:
            return productClass.getPrimaryHref()
        return ''


    security.declareProtected('View', 'getManufacturer')
    def getManufacturer(self):
        if self.productClass():
            return self.productClass().manufacturer()


    security.declareProtected('View', 'getManufacturerName')
    def getManufacturerName(self):
        """
        Gets the Manufacturer Name(Id)
        """
        manuf = self.getManufacturer()
        if manuf: return manuf.titleOrId()
        return ""


    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerLink(self, target=None):
        """
        Gets the Manufacturer PrimaryLink
        """
        if self.productClass():
            return self.productClass().manufacturer.getPrimaryLink(target)
        return ""


    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerHref(self):
        """
        Gets the Manufacturer's PrimaryHref
        """
        if self.productClass():
            return self.productClass().manufacturer.getPrimaryHref()
        return ""


    def getProductKey(self):
        """
        Return the arguments to the setProductKey method so we can avoid
        changing the object model when nothing has changed.
        """
        if self.productClass() is None:
            return ""
        elif self._manufacturer is not None:
            return (self._prodKey, self._manufacturer)
        elif self._prodKey is not None:
            return self._prodKey
        else:
            pclass = self.productClass()
            return pclass.getProductKey()

    def getProductLink(self, target=None):
        """
        Gets the Product's PrimaryLink
        """
        return self.productClass.getPrimaryLink(target)


    def getProductContext(self):
        """Return list of tuples with product context for this product.
        """
        prod = self.productClass()
        if prod:
            prodcontext = self.primaryAq()
            return prodcontext.zenPropertyItems()
        return []


    def setDescription(self, description):
        """
        Sets the description of the underlying ProductClass
        """

        prod = self.productClass()

        if prod:
            prod.description = description


    def getDescription(self):
        """
        Gets the description of the underlying ProductClass
        """

        prod = self.productClass()

        if prod: result = prod.description
        else   : result = None

        return result


    def getDeviceLink(self, screen='devicedetail'):
        return super(MEProduct, self).getDeviceLink(screen)

InitializeClass(MEProduct)
