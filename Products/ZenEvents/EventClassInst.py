import os
import copy
import re
import sre_constants
import logging
log = logging.getLogger("zen.Events")

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.EventView import EventView

def manage_addEventClassInst(context, id, REQUEST = None):
    """make a device class"""
    dc = EventClassInst(id)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 


addEventClassInst = DTMLFile('dtml/addEventClassInst',globals())


class EventClassPropertyMixin(object):

    def zenPropertyIds(self, all=True):
        props = super(EventClassPropertyMixin, self).zenPropertyIds(all)
        if all:
            for p in self.zEventProperties:
                p = "zEvent_" + p
                if p in props: continue
                props.append(p)
        return props


    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Apply event properties from EventClass.  List of property names is
        looked for in zProperty 'zEventProperties'. These properties are 
        looked up using the key 'zEvent_'+prop name (to prevent name clashes). 
        Any non-None property values are applied to the event.
        """
        evt._clearClasses = copy.copy(getattr(self, "zEventClearClasses", []))
        evt._action = getattr(self, "zEventAction", "status")
        propnames = getattr(self, "zEventProperties", ())
        for prop in propnames:
            propkey = "zEvent_" + prop
            value = getattr(self, propkey, None)
            if value != None:
                setattr(evt, prop, value)
        return evt



        
class EventClassInst(EventClassPropertyMixin, ZenModelRM, EventView):
    """
    EventClassInst.
    """

    event_key = meta_type = "EventClassInst"

    default_catalog = "eventClassSearch"

    zenRelationsBaseModule = "Products.ZenEvents"

    actions = ("status", "history", "heartbeat", "drop")

    _properties = (
        {'id':'eventClassKey', 'type':'string', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'rule', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        {'id':'explanation', 'type':'text', 'mode':'w'},
        {'id':'resolution', 'type':'text', 'mode':'w'},
        )


    _relations = (
        ("eventClass", ToOne(ToMany,"EventClass","instances")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'EventClassInst',
            'meta_type'      : 'EventClassInst',
            'description'    : """Base class for all devices""",
            'icon'           : 'EventClassInst.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addEventClassInst',
            'immediate_view' : 'eventClassInstStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'eventClassInstStatus'
                , 'permissions'   : (Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'eventClassInstEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'sequence'
                , 'name'          : 'Sequence'
                , 'action'        : 'eventClassInstSequence'
                , 'permissions'   : (Permissions.view,)
                },
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (Permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (Permissions.view, )
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def __init__(self, id):
        ZenModelRM.__init__(self, id)
        self.eventClassKey = id
        self.sequence = None
        self.rule = ""
        self.regex = ""    
        self.example = ""
        self.explanation = ""
        self.resolution = ""


    def getStatus(self, **kwargs):
        """Return the status number for this device of class statClass.
        """
        statkey = self.getEventClass
        return self.getEventManager().getStatusME(self, 
                                statusclass=self.getEventClass(), 
                                **kwargs)


    def getEventClass(self):
        """Return the full EventClass of this EventClassInst."""
        return self.getOrganizerName()


    def getDmdKey(self):
        """Return the dmd key of this mapping ie: /App/Start/zentinel
        """
        return self.getOrganizerName() + "/" + self.id


    def applyExtraction(self, evt):
        """
        Apply the event dict regex to extract additional values from the event.
        """
        if self.regex:
            m = re.search(self.regex, evt.summary)
            if m: evt.updateFromDict(m.groupdict())
        return evt


    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Apply event properties from EventClass.  List of property names is
        looked for in zProperty 'zEventProperties'. These properties are 
        looked up using the key 'zEvent_'+prop name (to prevent name clashes). 
        Any non-None property values are applied to the event.
        """
        evt.eventClass = self.getEventClass()
        return EventClassPropertyMixin.applyValues(self, evt)


    def ruleOrRegex(self, limit=None):
        """Return the rule if it exists else return the regex.
        limit limits the number of characters returned.
        """
        value = self.rule and self.rule or self.regex
        if not value and self.example:
            value = self.example
        if limit: value = value[:limit]
        return value


    def match(self, evt):
        """Match an event summary against our regex.
        """
        value = False
        log.debug("match on:%s", self.getPrimaryDmdId())
        if self.rule:
            try:
                log.debug("eval rule:%s", self.rule)
                value = eval(self.rule, {'evt':evt})
            except Exception, e:
                logging.warn("EventClassInst: %s rule failure: %s",
                            self.getDmdKey(), e)
        else:
            try:
                log.debug("regex='%s' summary='%s'", self.regex, evt.summary)
                value = re.search(self.regex, evt.summary, re.I)
            except sre_constants.error: pass
        return value

    
    def testRegexStyle(self):
        """Test our regex using the example event string.
        """
        if self.example:
            try:
                value = re.search(self.regex, self.example, re.I)
                if not value: return "color:#FF0000;"
            except sre_constants.error:
                return "color:#FF0000;"


    def testRuleStyle(self):
        """Test our rule by compiling it.
        """
        try:
            if self.rule:
                compile(self.rule, "<string>", "eval")
        except:
            return "color:#FF0000;"


    def sameKey(self):
        """Return a list of all mappings with the same eventClassKey.
        """
        return self.eventClass().find(self.eventClassKey)
        

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
            cat.catalog_object(self, self.id+self.regex)
            
                                                
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.id+self.regex)


    security.declareProtected('Manage DMD', 'manage_resequence')
    def manage_resequence(self, seqmap, REQUEST=None):
        """Reorder the sequence of eventClassMappings with the same key.
        """
        # first pass set new sequence
        for i, map in enumerate(self.sameKey()):
            map.sequence = seqmap[i]
        # second pass take out any holes
        for i, map in enumerate(self.sameKey()):
            map.sequence = i
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_editEventClassInst')
    def manage_editEventClassInst(self, name="", eventClassKey='',
                                regex='', rule='', example='', 
                                explanation='', resolution='', REQUEST=None):
        """Edit a EventClassInst from a web page.
        """
        redirect = self.rename(name)
        if self.eventClassKey != eventClassKey:
            self.unindex_object()
            self.sequence = self.eventClass().nextSequenceNumber(eventClassKey)
            self.eventClassKey = eventClassKey
            self.index_object()
        self.regex = regex
        self.rule = rule
        self.example = example
        self.explanation = explanation
        self.resolution = resolution
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(EventClassInst)
