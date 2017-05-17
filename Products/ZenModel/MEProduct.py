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
from Products.Zuul.catalog.indexable import ProductIndexable

from zope.event import notify
from Products.Zuul.catalog.events import IndexingEvent

class MEProduct(ManagedEntity, ProductIndexable):
    """
    MEProduct is a ManagedEntity that needs to track is manufacturer.
    For instance software and hardware.
    """

    PRODUCT_CLASS_ATTR = "product_class"

    _prodKey = None
    _manufacturer = None

    _relations = ManagedEntity._relations + (
        # Deprecated
        ("productClass", ToOne(ToMany, "Products.ZenModel.ProductClass", "instances")),
    )

    security = ClassSecurityInfo()

    def setProductClass(self, productClass):
        if productClass is None:
            self.removeProductClass()
        else:
            self._setObject(self.PRODUCT_CLASS_ATTR, productClass)
            notify(IndexingEvent(self, idxs="productClassId"))

    def removeProductClass(self):
        if self.hasObject(self.PRODUCT_CLASS_ATTR):
            self._delObject(self.PRODUCT_CLASS_ATTR)
            notify(IndexingEvent(self, idxs="productClassId"))

    def productClass(self):
        return getattr(self, self.PRODUCT_CLASS_ATTR, None)

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
        pc = self.productClass()
        if pc:
            return pc.manufacturer()


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
        pc = self.productClass()
        if pc:
            return pc.manufacturer.getPrimaryLink(target)
        return ""


    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerHref(self):
        """
        Gets the Manufacturer's PrimaryHref
        """
        pc = self.productClass()
        if pc:
            return pc.manufacturer.getPrimaryHref()
        return ""


    def getProductKey(self):
        """
        Return the arguments to the setProductKey method so we can avoid
        changing the object model when nothing has changed.
        """
        pc = self.productClass()
        if pc is None:
            return ""
        elif self._manufacturer is not None:
            return (self._prodKey, self._manufacturer)
        elif self._prodKey is not None:
            return self._prodKey
        else:
            return pc.getProductKey()

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
