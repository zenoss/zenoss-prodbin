#################################################################
#
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from Products.ZenModel.ZenModelRM import ZenModelRM

def manage_addActionRule(context, id, REQUEST=None):
    """Create an aciton rule"""
    ed = ActionRule(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addActionRule = DTMLFile('dtml/addActionRule',globals())

class ActionRule(ZenModelRM):
    """
    Rule applied to events that then executes an action on matching events.
    """
    
    meta_type = "ActionRule"

    where = "severity >= 4 and eventState = 0 and prodState = 1000"
    delay = 0
    action = "email"
    format = "%(device)s %(summary)s at %(firstTime)s"
    enabled = True
    actionTypes = ("page", "email") 

    _properties = ZenModelRM._properties + (
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'format', 'type':'text', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'action', 'type':'selection', 'mode':'w',
            'select_variable': 'actionTypes',},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
    )

    factory_type_information = ( 
        { 
            'id'             : 'ActionRule',
            'meta_type'      : 'ActionRule',
            'description'    : """Define action taken against events""",
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addActionRule',
            'immediate_view' : 'editActionRule',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editActionRule'
                , 'permissions'   : ("Change Settings",)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def getEventFields(self):
        """Return list of fields used in format.
        """
        return re.findall("%\((\S+)\)s", self.format)


    def checkFormat(self):
        """Check that the format string has valid fields.
        """
        evtfields = self.ZenEventManager.getFieldList()
        for field in self.getEventFields():
            if field not in evtfields:
                return False
        return True

    
    security.declareProtected('Change Settings', 'manage_editActionRule')
    def manage_editActionRule(self,  where="", delay=0, enabled=True, 
                              action="", REQUEST=None):
        """Update user settings.
        """
        self.where = where
        self.delay = delay
        self.enabled = enabled
        self.action = action
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)

InitializeClass(ActionRule)
