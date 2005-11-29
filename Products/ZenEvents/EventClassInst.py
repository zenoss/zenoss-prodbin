import os
import re
import sre_constants

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ManagedEntity import ManagedEntity

def manage_addEventClassInst(context, id, REQUEST = None):
    """make a device class"""
    dc = EventClassInst(id)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 


addEventClassInst = DTMLFile('dtml/addEventClassInst',globals())


class EventClassPropertyMixin(object):
    def zenPropertyIds(self, all=True):
        props = super(EventClassPropertyMixin, self).zenPropertyIds(all=True)
        if all:
            for p in self.zEventProperties:
                p = "zEvent_" + p
                if p in props: continue
                props.append(p)
        return props

        
class EventClassInst(EventClassPropertyMixin, ZenModelRM, ManagedEntity):
    """
    EventClassInst.
    """

    meta_type = "EventClassInst"

    event_key = "eventClass"

    default_catalog = "eventClassSearch"

    zenRelationsBaseModule = "Products.ZenEvents"

    
    _properties = (
        {'id':'eventClassKey', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        {'id':'explanation', 'type':'text', 'mode':'w'},
        {'id':'resolution', 'type':'text', 'mode':'w'},
        #{'id':'applyDeviceContext', 'type':'boolean', 'mode':'w'},
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
                , 'permissions'   : (Permissions.view, )
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
        self.regex = ""    
        self.example = ""
        self.explanation = ""
        self.resolution = ""
        #self.applyDeviceContext = False


    def getStatus(self, **kwargs):
        """Return the status number for this device of class statClass.
        """
        return self.getEventManager().getStatusME(self, 
                                statusclass=self.getEventClass(), **kwargs)


    def getEventClass(self):
        """Return the full EventClass of this EventClassInst."""
        return self.getOrganizerName()
    getDmdKey = getEventClass


    def applyExtraction(self, evt):
        """
        Apply the event dict regex to extract additional values from the event.
        """
        if not self.regex: return
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
        propnames = getattr(self, "zEventProperties", ())
        for prop in propnames:
            propkey = "zEvent_" + prop
            value = getattr(self, propkey, None)
            if value != None:
                setattr(evt, prop, value)
        return evt


    def match(self, summary):
        """Match an event summary against our regex.
        """
        try:
            return re.search(self.regex, summary)
        except sre_constants.error: pass
        return False

    
    def testRegexStyle(self):
        """Test our regex using the example event string.
        """
        if self.example and not self.match(self.example):
            return "color:#FF0000;"


    security.declareProtected('Manage DMD', 'rename')
    def rename(self, newId, REQUEST=None):
        """Delete device from the DMD"""
        parent = self.getPrimaryParent()
        parent.manage_renameObject(self.getId(), newId)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        if item == self: 
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
        if item == self or getattr(item, "_operation", -1) < 1: 
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


    security.declareProtected('Manage DMD', 'manage_editEventClassInst')
    def manage_editEventClassInst(self, eventClassKey='',
                                regex='', example='', explanation='', 
                                resolution='', REQUEST=None):
        """Edit a EventClassInst from a web page.
        """
        self.unindex_object()
        self.eventClassKey = eventClassKey
        self.regex = regex
        self.example = example
        self.explanation = explanation
        self.resolution = resolution
        self.index_object()
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST)


InitializeClass(EventClassInst)
