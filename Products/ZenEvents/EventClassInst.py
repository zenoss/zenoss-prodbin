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
    
    event_key = "EventClass"

    default_catalog = "eventClassSearch"

    zenRelationsBaseModule = "Products.ZenEvents"

    security = ClassSecurityInfo()

    _properties = (
        {'id':'eventClassKey', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'explanation', 'type':'text', 'mode':'w'},
        {'id':'resolution', 'type':'text', 'mode':'w'},
        {'id':'applyDeviceContext', 'type':'boolean', 'mode':'w'},
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
            'immediate_view' : 'EventClassInstOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'EventClassInstOverview'
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

    def __init__(self, id, eventClassKey=None):
        ZenModelRM.__init__(self, id)
        self.eventClassKey = eventClassKey
        if not eventClassKey:
            self.eventClassKey = id
        self.regex = ""    
        self.explanation = ""
        self.resolution = ""
        self.applyDeviceContext = False


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


InitializeClass(EventClassInst)
