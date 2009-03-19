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

Event class objects
"""

import types
import logging
log = logging.getLogger("zen.Events")

import transaction
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ManagedEntity import ManagedEntity
from Products.ZenModel.ZenossSecurity import *
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *
from EventClassInst import EventClassInst, EventClassPropertyMixin
from Products.ZenEvents.ZenEventClasses import Unknown

from Products.ZenModel.Organizer import Organizer
from Products.ZenModel.ZenPackable import ZenPackable

from Products.ZenUtils.Utils import prepId as globalPrepId

__pychecker__='no-argsused'

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

    transform = ''

    meta_type = "EventClass" #FIXME - this is wrong just temp perserving data
    event_key = "EventClass"

    dmdRootName = "Events"

    default_catalog = "eventClassSearch"

    _relations = ZenPackable._relations + (
        ("instances", ToManyCont(ToOne,"Products.ZenEvents.EventClassInst","eventClass")),
        )


    _properties = Organizer._properties + \
                  EventClassPropertyMixin._properties + \
                  ({'id':'transform', 'type':'text', 'mode':'w'},)


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
        ('Original', -1),
    )
    severities = dict([(b, a) for a, b in severityConversions])
    
    def getSubEventClasses(self):
        """
        Return all EventClass objects below this one.

        @return: list of event classes
        @rtype: list of EventClass
        """
        evts = self.children()
        for subgroup in self.children():
            evts.extend(subgroup.getSubEventClasses())
        return evts


    security.declareProtected(ZEN_COMMON, "getOrganizerNames")
    def getOrganizerNames(self, addblank=False, checkPerm=False):
        """
        Returns a list of all organizer names under this organizer. Overridden
        here so that restricted users can get a list of event classes.
        
        @param addblank: If True, add a blank item in the list.
        @type addblank: boolean
        @return: The DMD paths of all Organizers below this instance.
        @rtype: list
        @permission: ZEN_COMMON
        """
        return Organizer.getOrganizerNames(
            self, addblank=addblank, checkPerm=checkPerm)


    def find(self, evClassKey):
        """
        Look for the eventClassKey mapping in an event class,
        and return them in sequence number oder, lowest-to-highest.

        @parameter evClassKey: event class key
        @type evClassKey: string
        @return: list of event class mappings that match evClassKey, sorted
        @rtype: list of EventClassInst
        """
        cat = self._getCatalog()
        matches = cat({'eventClassKey': evClassKey})
        insts = [ self.getObjByPath(b.getPrimaryId) for b in matches ]
        insts.sort(lambda x,y: cmp(x.sequence, y.sequence))
        return insts

    
    def lookup(self, evt, device):
        """
        Given an event, return an event class organizer object

        @parameter evt: an event
        @type evt: dictionary
        @parameter device: device object
        @type device: DMD device
        @return: an event class that matches the mapping
        @rtype: EventClassInst
        """
        if device is None:
            try:
                return self.getDmdRoot("Events").getOrganizer(Unknown)
            except KeyError:
                log.debug("Unable to find 'Unknown' organizer")
                return None

        evtcls = []
        if getattr(evt, "eventClass", False):
            try:
                return self.getDmdRoot("Events").getOrganizer(evt.eventClass)
            except KeyError:
                log.debug("Unable to find '%s' organizer" % evt.eventClass)

        if getattr(evt, "eventClassKey", False):
            log.debug("lookup eventClassKey:%s", evt.eventClassKey)
            evtcls = self.find(evt.eventClassKey)

        if not evtcls: 
            log.debug("lookup eventClassKey:defaultmapping")
            evtcls = self.find("defaultmapping")

        for evtcl in evtcls:
            m = evtcl.match(evt, device)
            if m: 
                log.debug("EventClass:%s matched", evtcl.getOrganizerName())
                break
        else:
            log.debug("No EventClass matched")
            try:
                return self.getDmdRoot("Events").getOrganizer(Unknown)
            except KeyError:
                evtcl = None
                log.debug("Unable to find 'Unknown' organizer")
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
            rec = self.instances._getOb(id, None)
            if rec is None: continue
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

    def testTransformStyle(self):
        """Test our transform by compiling it.
        """
        try:
            if self.transform:
                compile(self.transform, "<string>", "exec")
        except:
            return "color:#FF0000;"

    def manage_editEventClassTransform(self, transform = '', REQUEST=None):
        "Save the transform"
        self.transform = transform
        if REQUEST: return self.callZenScreen(REQUEST)


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


    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'getOverriddenObjects')
    def getOverriddenObjects(self, propname, showDevices=False):
        """ 
        Get the objects that override a property somewhere below in the tree
        This method overrides ZenPropertyManager
        """
        objects = []
        for inst in self.getSubInstances('instances'):
            if inst.isLocal(propname) and inst not in objects:
                objects.append(inst) 
        for suborg in self.children():
            if suborg.isLocal(propname):
                objects.append(suborg)
            for inst in suborg.getOverriddenObjects(propname):
                if inst not in objects:
                    objects.append(inst)
        return objects
        
    security.declareProtected(ZEN_VIEW, 'getIconPath')
    def getIconPath(self):
        """ Override the zProperty icon path and return a folder
        """
        return "/zport/dmd/img/icons/folder.png"

    security.declareProtected(ZEN_VIEW, 'getPrettyLink')
    def getPrettyLink(self, noicon=False, shortDesc=False):
        """ Gets a link to this object, plus an icon """
        href = self.getPrimaryUrlPath().replace('%','%%')
        linktemplate = "<a href='"+href+"' class='prettylink'>%s</a>"
        icon = ("<div class='device-icon-container'> "
                "<img class='device-icon' src='%s'/> " 
                "</div>") % self.getIconPath()
        name = self.getPrimaryDmdId()
        if noicon: icon=''
        if shortDesc: name = self.id
        rendered = icon + name
        if not self.checkRemotePerm("View", self):
            return rendered
        else:
            return linktemplate % rendered

InitializeClass(EventClass)
