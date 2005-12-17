#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ManufacturerRoot

The Manufacturer classification class.  default identifiers and screens,
live here.

$Id: ManufacturerRoot.py,v 1.10 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import logging

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import Permissions as permissions

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenRelations.PrimaryPathObjectManager import \
    PrimaryPathBTreeFolder2

from ZenModelBase import ZenModelBase

def manage_addManufacturerRoot(context, REQUEST=None):
    """make a Manufacturer class"""
    id = "Manufacturers"
    m = ManufacturerRoot(id)
    context._setObject(id, m)
    m = context._getOb(id)
    m.createCatalog()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 


#addManufacturerRoot = DTMLFile('dtml/addManufacturerRoot',globals())


class ManufacturerRoot(ZenModelBase, PrimaryPathBTreeFolder2):
    """
    The root organizer for manufacturers.  May become a BtreeFolder2 at
    some point (to scale better).  Has interface to manage Manufacturers
    and the products that they create.
    """
    meta_type = "ManufacturerRoot"
    sub_classes = ('Manufacturer',) 
    default_catalog = "productSearch"

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Manufacturer',
            'meta_type'      : 'Manufacturer',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Manufacturer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addManufacturer',
            'immediate_view' : 'viewManufacturers',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturers'
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


    def manage_addManufacturer(self, manufacturerName, REQUEST=None):
        """Add a manufacturer from UI code.
        """
        self.createManufacturer(manufacturerName)
        if REQUEST: return self.callZenScreen(REQUEST)
       

    def manage_deleteManufacturers(self, ids=None, REQUEST=None):
        """Delete a list of manufacturers from UI.
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids: self._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    def createManufacturer(self, manufacturerName):
        """Return and create if nessesary manufacturerName.
        """
        from Products.ZenModel.Manufacturer import manage_addManufacturer
        if not self.has_key(manufacturerName):
            logging.info("Creating Manufacturer %s" % manufacturerName)
            manage_addManufacturer(self, manufacturerName)
        return self._getOb(manufacturerName)


    def getManufacturer(self, manufacturerName):
        """Return manufacturerName.
        """
        return self._getOb(manufacturerName)


    def getManufacturerNames(self):
        """return list of all companies"""
        return self.objectIds(spec=("Manufacturer"))


    def getProductNames(self, ManufacturerName):
        """return a list of all products this Manufacturer makes"""
        prods = [""]
        if hasattr(self, ManufacturerName):
            Manufacturer = self.getManufacturer(ManufacturerName)
            prods.extend(map(lambda x: x.getId(),
                Manufacturer.products.objectValuesAll()))
        prods.sort()
        return prods


    def findProduct(self, query):
        """Find a product by is productKey.
        """
        cat = getattr(self, self.default_catalog)
        brains = cat({'productKey': query})
        prods = [ self.unrestrictedTraverse(b.getPrimaryId) for b in brains ]
        if len(prods) == 1: return prods[0]

    
    def createHardwareProduct(self,prodName,manufacturer="Unknown",**kwargs):
        """Return and create if nessesary a HardwareClass object.
        """
        from Products.ZenModel.HardwareClass import HardwareClass
        return self._getProduct(prodName, manufacturer, HardwareClass, **kwargs)


    def createSoftwareProduct(self, prodName, manufacturer="Unknown", **kwargs):
        """Return and create if nesseary a SoftwareClass object.
        """
        from Products.ZenModel.SoftwareClass import SoftwareClass
        return self._getProduct(prodName, manufacturer, SoftwareClass, **kwargs)


    def _getProduct(self, prodName, manufacturer, factory, **kwargs):
        prod = None
        if not manufacturer or manufacturer == "Unknown":
            prod = self.findProduct(prodName) 
        if prod: return prod
        manufobj = self.getManufacturer(manufacturer)
        prod = manufobj._getOb(prodName, None)
        if not prod:
            prod = factory(prodName, **kwargs)
            manufobj.products._setObject(prod.id, prod)
            prod = manufobj.products._getOb(prod.id)
        return prod 


    def createCatalog(self):
        """Create a catalog for EventClassRecord searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('productKey', 'FieldIndex')
        zcat.addColumn('getPrimaryId')


InitializeClass(ManufacturerRoot)
