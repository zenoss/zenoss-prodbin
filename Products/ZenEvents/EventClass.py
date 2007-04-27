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
__doc__="""EventClass.py

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

import types
import logging
log = logging.getLogger("zen.Events")

import transaction
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *
from EventClassInst import EventClassInst, EventClassPropertyMixin

from Products.ZenModel.Organizer import Organizer
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenModel.ManagedEntity import ManagedEntity
from Products.ZenModel.ZenPackable import ZenPackable

from Products.ZenUtils.Utils import prepId as globalPrepId

def manage_addEventClass(context, id="Events", REQUEST=None):
    """make a event class"""
    ed = EventClass(id)
    context._setObject(id, ed)
    if id == "Events":
        ed = context._getOb(id)
        ed.createCatalog()
        ed.buildZProperties()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 


addEventClass = DTMLFile('dtml/addEventClass',globals())


class EventClass(EventClassPropertyMixin, Organizer, ManagedEntity, ZenPackable):
    """
    EventClass organizer
    """

    isInTree = True

    meta_type = "EventClass" #FIXME - this is wrong just temp perserving data
    event_key = "EventClass"

    dmdRootName = "Events"

    default_catalog = "eventClassSearch"

    _relations = ZenPackable._relations + (
        ("instances", ToManyCont(ToOne,"Products.ZenEvents.EventClassInst","eventClass")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'EventClass',
            'meta_type'      : 'EventClass',
            'description'    : """Base class for all event classes""",
            'icon'           : 'EventClass.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addEventClass',
            'immediate_view' : 'eventClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'classes'
                , 'name'          : 'Classes'
                , 'action'        : 'eventClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'eventList'
                , 'name'          : 'Mappings'
                , 'action'        : 'eventMappingList'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    severityConversions = (
        ('Critical', 5),
        ('Error', 4), 
        ('Warning', 3), 
        ('Info', 2), 
        ('Debug', 1), 
        ('Clear', 0), 
        ('Default', -1),
    )
    severities = dict([(b, a) for a, b in severityConversions])


    def zentinelTabs(self, templateName):
        if self.id == self.dmdRootName and templateName == 'viewEvents': 
            return []
        return super(EventClass, self).zentinelTabs(templateName)

    
    def getSubEventClasses(self):
        """Return all EventClass objects below this one.
        """
        evts = self.children()
        for subgroup in self.children():
            evts.extend(subgroup.getSubEventClasses())
        return evts


    def find(self, query):
        cat = self._getCatalog()
        brains = cat({'eventClassKey': query})
        insts = [ self.getObjByPath(b.getPrimaryId) for b in brains ]
        insts.sort(lambda x,y: cmp(x.sequence, y.sequence))
        return insts

    
    def lookup(self, evt, device):
        evtcls = []
        if getattr(evt, "eventClass", False):
            try:
                return self.getDmdRoot("Events").getOrganizer(evt.eventClass)
            except KeyError: pass
        elif getattr(evt, "eventClassKey", False):
            log.debug("lookup eventClassKey:%s", evt.eventClassKey)
            evtcls = self.find(evt.eventClassKey)
        if not evtcls: 
            log.debug("lookup eventClassKey:defaultmapping")
            evtcls = self.find("defaultmapping")
        recdict = {}
        for evtcl in evtcls:
            m = evtcl.match(evt, device)
            if m: 
                log.debug("EventClass:%s matched", evtcl.getOrganizerName())
                break
        else:
            evtcl = None
            log.debug("No EventClass matched")
        return evtcl


    def applyExtraction(self, evt):
        """Don't have extraction on event class.
        """
        return evt


    def getInstances(self):
        """Return all EventClassInstances from this node down.
        """
        insts = self.instances()
        for subclass in self.children():
            insts.extend(subclass.getInstances())
        return insts
   

    def nextSequenceNumber(self, key):
        """Get next sequence number for instance.
        """
        idx = 0
        insts = self.find(key)
        if len(insts) > 0:
            idx = insts[-1].sequence + 1
        return idx

    def prepId(self, id, subchar='_'):
        return globalPrepId(id, subchar)
            
    def createInstance(self, id=None, REQUEST=None):
        """Add an EventClassInst to this EventClass.
        """
        if id:
            id = self.prepId(id)
            c=0
            while self.instances._getOb(id,False):
                c+=1
                id = "%s_%02d" % (id, c)
            ecr = EventClassInst(id)
            ecr.sequence = self.nextSequenceNumber(ecr.eventClassKey)
            self.instances._setObject(id, ecr)
        if REQUEST: return self()
        return self.instances._getOb(id)


    def removeInstances(self, ids=None, REQUEST=None):
        """Remove Instances from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            self.instances._delObject(id)
        if REQUEST: return self()


    def moveInstances(self, moveTarget, ids=None, REQUEST=None):
        """Move instances from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.instances._getOb(id)
            rec._operation = 1 # moving object state
            self.instances._delObject(id)
            target.instances._setObject(id, rec)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def countInstances(self):
        """count all instances with in an event dict"""
        count = self.instances.countObjects()
        for group in self.children():
            count += group.countInstances()
        return count


    def buildZProperties(self):
        edict = self.getDmdRoot("Events")
        if getattr(aq_base(edict), "zEventAction", False): return
        edict._setProperty("zEventClearClasses", [], type="lines")
        edict._setProperty("zEventAction", "status")
        edict._setProperty("zEventSeverity", -1, type="int")
        #edict._setProperty("zEventProperties", [], type="lines")

    def getEventSeverities(self):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        return self.severityConversions

    def getEventSeverityString(self, severity):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        try:
            return self.severities[severity]
        except IndexError:
            return "Unknown"

    def reIndex(self):
        """Go through all ips in this tree and reindex them."""
        log.debug("reindexing EventClass:%s", self.getOrganizerName())
        zcat = self._getCatalog()
        zcat.manage_catalogClear()
        transaction.savepoint()
        for evtclass in self.getSubEventClasses():
            for ip in evtclass.instances(): 
                ip.index_object()
        transaction.savepoint()


    def createCatalog(self):
        """Create a catalog for EventClassRecord searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('eventClassKey', 'FieldIndex')
        zcat.addColumn('getPrimaryId')


InitializeClass(EventClass)
