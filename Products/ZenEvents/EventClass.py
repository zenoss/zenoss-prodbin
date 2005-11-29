__doc__="""EventClass.py

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

import types

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.Organizer import Organizer
from Products.ZenModel.ManagedEntity import ManagedEntity
from EventClassInst import EventClassInst

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


class EventClass(Organizer, ManagedEntity):
    """
    EventClass organizer
    """

    isInTree = True

    dmdRootName = "Events"

    meta_type = event_key = "eventClass"

    default_catalog = "eventClassSearch"

    zenRelationsBaseModule = "Products.ZenEvents"


    _relations = (
        ("instances", ToManyCont(ToOne,"EventClassInst","eventClass")),
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
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'eventClassStatus'
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
                , 'action'        : 'viewDeviceClassConfig'
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


    def find(self, query):
        cat = getattr(self, self.default_catalog)
        brains = cat({'eventClassKey': query})
        return [ self.unrestrictedTraverse(b.getPrimaryId) for b in brains ]

    
    def lookup(self, evt):
        if not getattr(evt, "eventClassKey", False): return None
        evtrecs = self.find(evt.eventClassKey)
        recdict = {}
        if len(evtrecs) == 1:
            return evtrec
        for evtrec in evtrecs:
            m = evtrec.match(evt.summary)
            if m: break
        return evtrec


    def createInstance(self, id, REQUEST=None):
        """Add an EventClassInst to this EventClass.
        """
        ecr = EventClassInst(id)
        self.instances._setObject(id, ecr)
        if REQUEST: return self()
        else: return id 


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
        if getattr(aq_base(edict), "zEventProperties", False): return
        edict._setProperty("zEventProperties", ["severity"], 
                            type="lines")


    def createCatalog(self):
        """Create a catalog for EventClassRecord searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('eventClassKey', 'FieldIndex')
        zcat.addColumn('getPrimaryId')


InitializeClass(EventClass)
