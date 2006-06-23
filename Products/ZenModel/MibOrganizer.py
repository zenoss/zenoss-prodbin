#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *

from Organizer import Organizer
from MibModule import MibModule

def manage_addMibOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = MibOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMibOrganizer = DTMLFile('dtml/addMibOrganizer',globals())


class MibOrganizer(Organizer):
    """
    DeviceOrganizer is the base class for device organizers.
    It has lots of methods for rolling up device statistics and information.
    """
    meta_type = "MibOrganizer"
    dmdRootName = "Mibs"
    default_catalog = 'mibSearch'
    
    security = ClassSecurityInfo()

    _relations = (
        ("mibs", ToManyCont(ToOne,"MibModule","miborganizer")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'mibOrganizerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'mibOrganizerOverview'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )


    def __init__(self, id=None):
        if not id: id = self.dmdRootName
        super(MibOrganizer, self).__init__(id)
        if self.id == self.dmdRootName:
            self.createCatalog()
   

    def countClasses(self):
        """Count all mibs with in a MibOrganizer.
        """
        count = self.mibs.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    def createMibModule(self, name, path="/"):
        """Create a MibModule 
        """
        mibs = self.getDmdRoot(self.dmdRootName)
        #mod = mibs.findMibModule(name)
        mod = None
        if not mod: 
            modorg = mibs.createOrganizer(path)
            mod = MibModule(name) 
            modorg.mibs._setObject(mod.id, mod)
            modcl = modorg.mibs._getOb(mod.id)
        return mod

    
    def manage_addMibModule(self, id, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        mm = MibModule(id)
        self.mibs._setObject(id, mm)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        else:
            return self.mibs._getOb(id)

    
    def removeMibModules(self, ids=None, REQUEST=None):
        """Remove MibModules from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            self.mibs._delObject(id)
        if REQUEST: return self()


    def moveMibModules(self, moveTarget, ids=None, REQUEST=None):
        """Move MibModules from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.mibs._getOb(id)
            rec._operation = 1 # moving object state
            self.mibs._delObject(id)
            target.mibs._setObject(id, rec)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for srv in self.getSubOrganizers():
            for inst in srv.mibs(): 
                inst.index_object()


    def createCatalog(self):
        """Create a catalog for mibs searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('oids', 'KeywordIndex')
        zcat.addIndex('summary', 'KeywordIndex')
        zcat.addColumn('getPrimaryId')




InitializeClass(MibOrganizer)

