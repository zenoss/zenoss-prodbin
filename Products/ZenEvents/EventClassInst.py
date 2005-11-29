from Globals import DTMLFile
from Globals import InitializeClass
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

class EventClassInst(ZenModelRM, ManagedEntity):

    meta_type = "EventClassInst"
    
    event_key = "eventClass"

    default_catalog = "eventClassSearch"

    zenRelationsBaseModule = "Products.ZenEvents"

    _properties = (
        {'id':'className', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
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
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'eventClassInstEdit'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'viewDeviceClassConfig'
                , 'permissions'   : ("Change Device",)
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

    def __init__(self, id, className=None):
        ZenModelRM.__init__(self, id)
        self.className = className
        if not className:
            self.className = id
        self.regex = ""    
        self.explanation = ""
        self.resolution = ""
        #self.applyDeviceContext = False


    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        """

    def match(self, evt):
        """Match an event summary against our regex.
        """
        if not self.regex: return False
        if not getattr(aq_base(self), "_v_cregex", False):
            self._v_cregex = re.compile(self.regex)
        return self._v_cregex.search(evt.summary)


    security.declareProtected('Manage DMD', 'manage_editEventClassInst')
    def manage_editEventClassInst(self, className='', regex='', explanation='', 
                                resolution='', REQUEST=None):
        """Edit a EventClassInst from a web page.
        """
        self.className = className
        self.regex = regex
        self.explanation = explanation
        self.resolution = resolution
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST)


InitializeClass(EventClassInst)
