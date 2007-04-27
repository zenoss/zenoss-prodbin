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

import re
import types
import logging
log = logging.getLogger("zen.OSProcessOrganizer")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from ZenPackable import ZenPackable

from Organizer import Organizer
from OSProcessClass import OSProcessClass

def manage_addOSProcessOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = OSProcessOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addOSProcessOrganizer = DTMLFile('dtml/addOSProcessOrganizer',globals())

class OSProcessOrganizer(Organizer, Commandable, ZenPackable):
    meta_type = "OSProcessOrganizer"
    dmdRootName = "Processes"
    #default_catalog = "osprocessSearch"

    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 

    _relations = Organizer._relations + ZenPackable._relations + (
        ("osProcessClasses", ToManyCont(
            ToOne,"Products.ZenModel.OSProcessClass","osProcessOrganizer")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'osProcessOrganizerOverview',
            'actions'        :
            ( 
                { 'id'            : 'classes'
                , 'name'          : 'Classes'
                , 'action'        : 'osProcessOrganizerOverview'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'resequence'
                , 'name'          : 'Sequence'
                , 'action'        : 'osProcessResequence'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'osProcessOrganizerManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
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
        super(OSProcessOrganizer, self).__init__(id)
        if self.id == self.dmdRootName:
            self.buildZProperties()


    def getSubOSProcessClassesGen(self):
        """Return generator that goes through all process classes.
        """
        for proc in self.osProcessClasses.objectValuesGen():
            yield proc
        for subgroup in self.children():
            for proc in subgroup.getSubOSProcessClassesGen():
                yield proc

        
    def countClasses(self):
        """Count all osprocessclasses with in a ServiceOrganizer.
        """
        count = self.osProcessClasses.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    def manage_addOSProcessClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = OSProcessClass(id)
            sc.sequence = len(self.osProcessClasses()) 
            self.osProcessClasses._setObject(id, sc)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        else:
            return self.osProcessClasses._getOb(id)


    def manage_resequenceProcesses(self, seqmap=(), origseq=(), REQUEST=None):
        "resequence the OsProcesses"
        from Products.ZenUtils.Utils import resequence
        return resequence(self,
                          self.osProcessClasses(), seqmap, origseq, REQUEST)
    
    def unmonitorOSProcessClasses(self, ids=None, REQUEST=None):
        return self.monitorOSProcessClasses(ids, False, REQUEST)

   
    def monitorOSProcessClasses(self, ids=None, monitor=True, REQUEST=None):
        """Remove OSProcessClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            svc = self.osProcessClasses._getOb(id)
            svc.setZenProperty("zMonitor", monitor)
        if REQUEST: return self()


    def removeOSProcessClasses(self, ids=None, REQUEST=None):
        """Remove OSProcessClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            # delete related os process instances
            klass = self.osProcessClasses[id]
            for p in klass.instances():
                p.device().os.processes._delObject(p.id)
            self.osProcessClasses._delObject(id)
        self.manage_resequenceProcesses()
        if REQUEST: return self()


    def moveOSProcessClasses(self, moveTarget, ids=None, REQUEST=None):
        """Move OSProcessClasses from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.osProcessClasses._getOb(id)
            rec._operation = 1 # moving object state
            self.osProcessClasses._delObject(id)
            target.osProcessClasses._setObject(id, rec)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def buildZProperties(self):
        if hasattr(aq_base(self), "zCountProcs"): return
        self._setProperty("zCountProcs", False, type="boolean")
        self._setProperty("zAlertOnRestart", False, type="boolean")
        self._setProperty("zMonitor", True, type="boolean")
        self._setProperty("zFailSeverity", 4, type="int")


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        targets = []
        for osc in self.osProcessClasses():
            targets += osc.getUserCommandTargets()
        for org in self.children():
            targets += org.getUserCommandTargets()
        return targets            


InitializeClass(OSProcessOrganizer)
