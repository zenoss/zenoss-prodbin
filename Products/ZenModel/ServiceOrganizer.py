#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types
import logging
log = logging.getLogger("zen.ServiceOrganizer")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *

from Organizer import Organizer
from ServiceClass import ServiceClass, getIpServiceKey

def manage_addServiceOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = ServiceOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if sc.id == sc.dmdRootName:
        sc.createCatalog()
        sc.buildZProperties()

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addServiceOrganizer = DTMLFile('dtml/addServiceOrganizer',globals())

class ServiceOrganizer(Organizer):
    meta_type = "ServiceOrganizer"
    dmdRootName = "Services"
    default_catalog = "serviceSearch"

    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 

    _relations = (
        ("serviceclasses", ToManyCont(ToOne,"ServiceClass","serviceorganizer")),
        )

    factory_type_information = ( 
        { 
            'id'             : 'ServiceOrganizer',
            'meta_type'      : 'ServiceOrganizer',
            'icon'           : 'ServiceOrganizer.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServiceOrganizer',
            'immediate_view' : 'serviceOrganizerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'serviceOrganizerOverview'
                , 'permissions'   : (
                  Permissions.view, )
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
    
    def __init__(self, id=None):
        if not id: id = self.dmdRootName
        super(ServiceOrganizer, self).__init__(id)
        if self.id == self.dmdRootName:
            self.createCatalog()
            self.buildZProperties()
   

    def find(self, query):
        """Find a service class by is serviceKey.
        """
        cat = getattr(self, self.default_catalog, None)
        if not cat: return 
        brains = cat({'serviceKeys': query})
        try:
            prods = [self.unrestrictedTraverse(b.getPrimaryId) for b in brains ]
        except KeyError:
            log.exception(", ".join([b.getPrimaryId for b in brains]))
            raise
        if len(prods) == 1: return prods[0]

    
    def countClasses(self):
        """Count all serviceclasses with in a ServiceOrganizer.
        """
        count = self.serviceclasses.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    def createServiceClass(self, protocol="", port=0, name="", description="",
                            factory=ServiceClass):
        """Create a service class (or retrun existing) based on keywords.
        """
        if name:
            key = name
            if description: dpath = "/WinService/"
        elif protocol and port > 0:
            key = getIpServiceKey(protocol, port)
            dpath = "/IpService/"

        svcs = self.getDmdRoot(self.dmdRootName)
        svccl = svcs.find(key)
        if not svccl: 
            svcorg = svcs.createOrganizer(dpath)
            svccl = factory(key, (key,),port=port,description=description)
            svcorg.serviceclasses._setObject(svccl.id, svccl)
            svccl = svcorg.serviceclasses._getOb(svccl.id)
        return svccl 

    
    def manage_addServiceClass(self, id, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        sc = ServiceClass(id)
        self.serviceclasses._setObject(id, sc)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        else:
            return self.serviceclasses._getOb(id)

    
    def unmonitorServiceClasses(self, ids=None, REQUEST=None):
        return self.monitorServiceClasses(self, ids, False, REQUEST)

   
    def monitorServiceClasses(self, ids=None, monitor=True, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            svc = self.serviceclasses._getOb(id)
            svc.setZenProperty("zMonitor", monitor)
        if REQUEST: return self()


    def removeServiceClasses(self, ids=None, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            self.serviceclasses._delObject(id)
        if REQUEST: return self()


    def moveServiceClasses(self, moveTarget, ids=None, REQUEST=None):
        """Move ServiceClasses from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.serviceclasses._getOb(id)
            rec._operation = 1 # moving object state
            self.serviceclasses._delObject(id)
            target.serviceclasses._setObject(id, rec)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def buildZProperties(self):
        if hasattr(aq_base(self), "zMonitor"): return
        self._setProperty("zMonitor", False, type="boolean")
        self._setProperty("zFailSeverity", 5, type="int")
        self._setProperty("zHideFieldsFromList", [], type="lines")


    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for srv in self.getSubOrganizers():
            for inst in srv.serviceclasses(): 
                inst.index_object()


    def createCatalog(self):
        """Create a catalog for ServiceClass searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('serviceKeys', 'KeywordIndex')
        zcat.addColumn('getPrimaryId')



InitializeClass(ServiceOrganizer)
