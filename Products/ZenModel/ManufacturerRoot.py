#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ManufacturerRoot

The Manufacturer classification class.  default identifiers and screens,
live here.

$Id: ManufacturerRoot.py,v 1.10 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import logging

import transaction

from Globals import InitializeClass
from Globals import DTMLFile
from Acquisition import aq_base
from AccessControl import Permissions as permissions

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenRelations.PrimaryPathObjectManager import \
    PrimaryPathBTreeFolder2

from ZenModelBase import ZenModelBase
from Products.ZenUtils.Search import makeCaseSensitiveKeywordIndex

def manage_addManufacturerRoot(context, REQUEST=None):
    """make a Manufacturer class"""
    m = ManufacturerRoot()
    context._setObject(m.getId(), m)
    m = context._getOb(m.dmdRootName)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


#addManufacturerRoot = DTMLFile('dtml/addManufacturerRoot',globals())


class ManufacturerRoot(ZenModelBase, PrimaryPathBTreeFolder2):
    """
    The root organizer for manufacturers.  May become a BtreeFolder2 at
    some point (to scale better).  Has interface to manage Manufacturers
    and the products that they create.
    """
    dmdRootName = "Manufacturers"
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


    def __init__(self, id=None):
        if not id: id = self.dmdRootName
        super(ManufacturerRoot, self).__init__(id)
        self.createCatalog()
        self.buildzProperties()


    def manage_addManufacturer(self, manufacturerName=None, REQUEST=None):
        """Add a manufacturer from UI code.
        """
        if manufacturerName:
            self.createManufacturer(manufacturerName)
        if REQUEST: return self.callZenScreen(REQUEST)
       

    def manage_deleteManufacturers(self, ids=None, REQUEST=None):
        """Delete a list of manufacturers from UI.
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids: self._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    def createManufacturer(self, manufacturerName=None):
        """Return and create if nessesary manufacturerName.
        """
        from Products.ZenModel.Manufacturer import manage_addManufacturer
        if manufacturerName and not self.has_key(manufacturerName):
            logging.info("Creating Manufacturer %s" % manufacturerName)
            manage_addManufacturer(self, manufacturerName)
        if manufacturerName:
            return self._getOb(manufacturerName)
        return None


    def getManufacturer(self, manufacturerName):
        """Return manufacturerName.
        If trying to get Unknown and it doesn't exist, create it
        """
        createOnDemand = ['Unknown']
        if not self.has_key(manufacturerName) \
            and manufacturerName in createOnDemand:
            man = self.createManufacturer(manufacturerName)
        else:
            man = self._getOb(manufacturerName)
        return man

    def getManufacturerNames(self):
        """return list of all companies"""
        return self.objectIds(spec=("Manufacturer"))


    def getProductNames(self, mname, type=None):
        """return a list of all products this Manufacturer makes"""
        prods = [""]
        if hasattr(self, mname):
            manuf = self.getManufacturer(mname)
            prods.extend(manuf.products.objectIds(spec=type))
        prods.sort()
        return prods


    def findProduct(self, query):
        """Find a product by is productKey.
        """
        cat = getattr(self, self.default_catalog, None)
        if not cat: return 
        brains = cat({'productKeys': query})
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
        prodid = self.prepId(prodName)
        if not manufacturer or manufacturer == "Unknown":
            prod = self.findProduct(prodName)
        if prod: return prod
        manufobj = self.getManufacturer(manufacturer)
        prod = manufobj._getOb(prodid, None)
        if not prod:
            prod = factory(prodid, prodName=prodName, **kwargs)
            manufobj.products._setObject(prodid, prod)
            prod = manufobj.products._getOb(prodid)
        return prod


    def getProductsGen(self):
        """Return a generator that gets all products.
        """
        for manuf in self.values(spec="Manufacturer"):
            for prod in manuf.products.objectValuesGen():
                yield prod
        
    
    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        transaction.savepoint()
        for i, prod in enumerate(self.getProductsGen()):
            prod.index_object()
            if not i % 1000: transaction.savepoint()


    def createCatalog(self):
        """Create a catalog for EventClassRecord searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX update to use ManagableIndex
        manage_addZCatalog(self, self.default_catalog,
            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('productKeys', makeCaseSensitiveKeywordIndex('productKeys'))
        zcat.addColumn('getPrimaryId')


    def exportXml(self, ofile, ignorerels=[], root=False):
        """Return an xml based representation of a RelationshipManager
        <object id='/Devices/Servers/Windows/dhcp160.confmon.loc' 
            module='Products.Confmon.IpInterface' class='IpInterface'>
            <property id='name'>jim</property>
            <toone></toone>
            <tomany></tomany>
            <tomanycont></tomanycont>
        </object>
        """
        modname = self.__class__.__module__
        classname = self.__class__.__name__
        id = root and self.getPrimaryId() or self.id
        stag = "<object id='%s' module='%s' class='%s'>\n" % (
                    id , modname, classname)
        ofile.write(stag)
        for obj in self.objectValues():
            if getattr(aq_base(obj), 'exportXml', False):
                obj.exportXml(ofile, ignorerels)
        ofile.write("</object>\n")

        
    def buildzProperties(self):
        if getattr(aq_base(self), "zDeviceClass", False): return
        self._setProperty("zDeviceClass", "")
        self._setProperty("zDeviceGroup", "")
        self._setProperty("zSystem", "")


InitializeClass(ManufacturerRoot)
