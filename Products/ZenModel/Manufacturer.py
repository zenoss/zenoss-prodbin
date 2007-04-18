#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Manufacturer

Manufacturer is a base class that represents a vendor of Products.

$Id: Manufacturer.py,v 1.11 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

import types

from Globals import DTMLFile, InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


def manage_addManufacturer(context, id=None, REQUEST = None):
    """make a Manufacturer"""
    if id:
        d = Manufacturer(id)
        context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addManufacturer = DTMLFile('dtml/addManufacturer',globals())

class Manufacturer(ZenModelRM, ZenPackable):
    """Manufacturer object"""
    portal_type = meta_type = 'Manufacturer'

    url = ''
    supportNumber = ''
    address1 = ''
    address2 = ''
    city = ''
    state = ''
    zip = ''

    _properties = (
        {'id':'url', 'type':'string', 'mode':'w'},
        {'id':'supportNumber', 'type':'string', 'mode':'w'},
        {'id':'address1', 'type':'string', 'mode':'w'},
        {'id':'address2', 'type':'string', 'mode':'w'},
        {'id':'city', 'type':'string', 'mode':'w'},
        {'id':'state', 'type':'string', 'mode':'w'},
        {'id':'zip', 'type':'string', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("products", ToManyCont(ToOne,"Products.ZenModel.ProductClass","manufacturer")),
    )
 
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Manufacturer',
            'meta_type'      : 'Manufacturer',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Manufacturer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addManufacturer',
            'immediate_view' : 'viewManufacturerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturerOverview'
                , 'permissions'   : (permissions.view, )
                },
                #{ 'id'            : 'edit'
                #, 'name'          : 'Edit'
                #, 'action'        : 'editManufacturer'
                #, 'permissions'   : ("Manage DMD", )
                #},
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Changes'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (permissions.view, )
#                },
            )
          },
        )

    security = ClassSecurityInfo()


    def count(self):
        """Return the number of products for this manufacturer.
        """
        return self.products.countObjects()


    def manage_addHardware(self, prodName=None, REQUEST=None):
        """Add a hardware product from UI code.
        """
        if prodName:
            from Products.ZenModel.HardwareClass import HardwareClass
            self._getProduct(prodName, HardwareClass)
        if REQUEST: return self.callZenScreen(REQUEST)


    def manage_addSoftware(self, prodName=None, REQUEST=None):
        """Add a software product from UI code.
        """
        if prodName:
            from Products.ZenModel.SoftwareClass import SoftwareClass
            self._getProduct(prodName, SoftwareClass)
        if REQUEST: return self.callZenScreen(REQUEST)

   
    def moveProducts(self, moveTarget=None, ids=None, REQUEST=None):
        """Move product to different manufacturer.
        """
        if not moveTarget or not ids: return self()
        target = self.getManufacturer(moveTarget)
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            obj = self.products._getOb(id)
            obj._operation = 1 # moving object state
            self.products._delObject(id)
            target.products._setObject(id, obj)
        #if REQUEST:
        #    REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
        if REQUEST: return self.callZenScreen(REQUEST)


    def _getProduct(self, prodName, factory):
        """Add a product to this manufacturer based on its factory type.
        """
        prod = self._getOb(prodName, None)
        if not prod:
            prod = factory(prodName)
            self.products._setObject(prod.id, prod)
            prod = self.products._getOb(prod.id)
        return prod 


    def manage_deleteProducts(self, ids=None, REQUEST=None):
        """Delete a list of products from UI.
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids: self.products._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    def getProductNames(self):
        """return a list of all products this Manufacturer makes"""
        prods = [""]
        prods.extend(map(lambda x: x.getId(),
                Manufacturer.products.objectValuesAll()))
        prods.sort()
        return prods


    security.declareProtected('Manage DMD', 'manage_editManufacturer')
    def manage_editManufacturer(self, id='',
                url = '', supportNumber = '',
                address1 = '', address2 = '',
                city = '', state = '', zip = '', REQUEST=None):
        """
        Edit a Manufacturer from a web page.
        """
        redirect = self.rename(id)
        self.url = url
        self.supportNumber = supportNumber
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zip = zip
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(Manufacturer)
