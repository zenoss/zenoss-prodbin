###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import types

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex

from Organizer import Organizer
from MibModule import MibModule
from ZenPackable import ZenPackable

def manage_addMibOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = MibOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

addMibOrganizer = DTMLFile('dtml/addMibOrganizer',globals())


class MibOrganizer(Organizer, ZenPackable):
    """
    DeviceOrganizer is the base class for device organizers.
    It has lots of methods for rolling up device statistics and information.
    """
    meta_type = "MibOrganizer"
    dmdRootName = "Mibs"
    default_catalog = 'mibSearch'
    
    security = ClassSecurityInfo()

    _relations = Organizer._relations + ZenPackable._relations + (
        ("mibs", ToManyCont(ToOne,"Products.ZenModel.MibModule","miborganizer")),
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
                , 'name'          : 'Modifications'
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
  

    def oid2name(self, oid):
        """Return a name in for and oid.
        """
        brains = self.getDmdRoot("Mibs").mibSearch({'oid': oid})
        if len(brains) > 0: return brains[0].id
        return ""

     
    def name2oid(self, name):
        """Return an oid based on a name in the form MIB::name.
        """
        brains = self.getDmdRoot("Mibs").mibSearch({'id': name})
        if len(brains) > 0: return brains[0].oid
        return ""


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
        mod = None
        if not mod:
            modorg = mibs.createOrganizer(path)
            mod = MibModule(name)
            modorg.mibs._setObject(mod.id, mod)
            mod = modorg.mibs._getOb(mod.id)
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
        for mibmod in self.mibs():
            mibmod.index_object()
        for miborg in self.getSubOrganizers():
            for mibmod in miborg.mibs():
                mibmod.index_object()


    def createCatalog(self):
        """Create a catalog for mibs searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX update to use ManagableIndex
        manage_addZCatalog(self, self.default_catalog, self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('oid', makeCaseInsensitiveKeywordIndex('oid'))
        cat.addIndex('id', makeCaseInsensitiveKeywordIndex('id'))
        cat.addIndex('summary', makeCaseInsensitiveKeywordIndex('summary'))
        zcat.addColumn('getPrimaryId')
        zcat.addColumn('id')
        zcat.addColumn('oid')




InitializeClass(MibOrganizer)

