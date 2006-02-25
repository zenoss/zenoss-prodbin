#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ServiceClass

The service classification class.  default identifiers, screens,
and data collectors live here.

$Id: ServiceClass.py,v 1.9 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


def getIpServiceKey(protocol, port):
    return "%s-%05d" % (protocol, port)


def manage_addServiceClass(context, id, REQUEST = None):
    """make a device class"""
    sc = ServiceClass(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    sc.createCatalog()
    sc.buildZProperties()

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addServiceClass = DTMLFile('dtml/addServiceClass',globals())

class ServiceClass(ZenModelRM):
    meta_type = "ServiceClass"
    dmdRootName = "Services"
    default_catalog = "serviceSearch"

    name = ""
    serviceKeys = ()
    description = ""
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'serviceKeys', 'type':'lines', 'mode':'w'},
        {'id':'caption', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'contact', 'type':'string', 'mode':'w'},
        ) 

    _relations = (
        ("instances", ToMany(ToOne, "Service", "serviceclass")),
        ("serviceorganizer", 
            ToOne(ToManyCont,"ServiceOrganizer","serviceclasses")),
        )


    factory_type_information = ( 
        { 
            'id'             : 'ServiceClass',
            'meta_type'      : 'ServiceClass',
            'icon'           : 'ServiceClass.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServiceClass',
            'immediate_view' : 'serviceClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'serviceClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'serviceClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
   

    def __init__(self, id, serviceKeys=(), description=""):
        id = self.prepId(id)
        super(ServiceClass, self).__init__(id)
        self.name = id
        self.serviceKeys = serviceKeys
        self.description = description
  

    def addServiceKey(self, key):
        """Add a key to the service keys.
        """
        if key not in self.serviceKeys:
            self.serviceKeys = self.serviceKeys + (key,)
            self.index_object()


    def count(self):
        """Return count of instances in this class.
        """
        return self.instances.countObjects()


    def getServiceClassName(self):
        """Return the full name of this service class.
        """
        return self.getPrimaryDmdId("Services", "serviceclasses")


    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
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
        ZenModelRM.manage_beforeDelete(self, item, container)
        self.unindex_object()


    def index_object(self):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.getPrimaryId())
            
                                                
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.getPrimaryId())


    security.declareProtected('Manage DMD', 'manage_editServiceClass')
    def manage_editServiceClass(self, name="", monitor=False, serviceKeys=[],
                               port=0, description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        self.name = name
        id = self.prepId(name)
        if self.zMonitor != monitor:
            self.setZenProperty("zMonitor", monitor)
        redirect = self.rename(id)
        serviceKeys = [ l.strip() for l in serviceKeys.split('\n') ]
        if serviceKeys != self.serviceKeys:
            self.unindex_object()
            self.serviceKeys = serviceKeys
            self.index_object()
        self.port = port
        self.description = description        
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST, redirect)
   


InitializeClass(ServiceClass)
