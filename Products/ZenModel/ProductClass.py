##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from zope.interface import implements

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)
from Products.ZenWidgets import messaging

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)

class ProductClass(ZenModelRM, ZenPackable):
    implements(IIndexed)
    meta_type = "ProductClass"

    #itclass = ""
    name = ""
    productKeys = []
    isOS = False

    default_catalog = "productSearch"

    _properties = (
        #{'id':'itclass', 'type':'string', 'mode':'w'},
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'productKeys', 'type':'lines', 'mode':'w'},
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        {'id':'isOS', 'type':'boolean', 'mode':'w'},
    )

    _relations = ZenPackable._relations + (
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
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEditNew'
                , 'permissions'   : ("Manage DMD",)
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
            # When adding manually through the gui or via device discovery if
            # the device model is not already in the system, both prodName
            # and productKey will be None
            self.productKeys = [id]
        self.name = prodName if prodName is not None else id
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


    def getManufacturerName(self):
        if not self.manufacturer():
            return ''
        return self.manufacturer().getId()


    security.declareProtected('Manage DMD', 'manage_editProductClass')
    def manage_editProductClass(self, name="", productKeys=(), isOS=False,
                               partNumber="", description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        redirect = self.rename(name)
        productKeys = [ l.strip() for l in productKeys.split('\n') ]
        if productKeys != self.productKeys:
            self.unindex_object()
            self.productKeys = productKeys
        self.partNumber = partNumber
        self.description = description
        self.isOS = isOS
        self.name = name
        self.index_object()
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Product Class Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(ProductClass)
