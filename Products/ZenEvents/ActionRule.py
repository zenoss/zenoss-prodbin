#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import re
import logging
log = logging.getLogger("zen.ActionRule")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_parent

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
    format = "%(device)s %(summary)s"
    body =  "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severity)s\n" \
            "Time: %(firstTime)s:\n" \
            "Message:\n%(message)s\n" \
            "Event: %(eventUrl)s\n" 
    clearFormat = "CLEAR: %(device)s %(clearSummary)s"
    clearBody =  \
            "Event: '%(summary)s'\n" \
            "Cleared by: '%(clearSummary)s'\n" \
            "At: %(clearFirstTime)s\n" \
            "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severity)s\n" \
            "Message:\n%(message)s\n"
    enabled = False
    actionTypes = ("page", "email") 
    targetAddr = ""

    _properties = ZenModelRM._properties + (
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'format', 'type':'text', 'mode':'w'},
        {'id':'body', 'type':'text', 'mode':'w'},
        {'id':'clearFormat', 'type':'text', 'mode':'w'},
        {'id':'clearBody', 'type':'text', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'action', 'type':'selection', 'mode':'w',
            'select_variable': 'actionTypes',},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'targetAddr', 'type':'string', 'mode':'w'},
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


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(ActionRule, self).breadCrumbs(terminator)
        url = aq_parent(self).absolute_url_path() + "/editActionRules"
        crumbs.insert(-1,(url,'Alerting Rules'))
        return crumbs


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


    def getAddress(self):
        """Return the correct address for the action this rule uses.
        """
        if self.targetAddr:
            return self.targetAddr
        elif self.action == "page":
            return self.pager
        elif self.action == "email":
            return self.email


    def getUserid(self):
        """Return the userid this action is for.
        """
        return self.getPrimaryParent().getId()

    
    security.declareProtected('Change Settings', 'manage_editActionRule')
    def manage_editActionRule(self, REQUEST=None):
        """Update user settings.
        """
        if not self.enabled:
            self._clearAlertState()
        return self.zmanage_editProperties(REQUEST)


    def manage_beforeDelete(self, item, container):
        """Clear state in alert_state before we are deleted.
        """
        self._clearAlertState()


    def _clearAlertState(self):
        """Clear state in alert_state before we are deleted.
        """
        db = self.ZenEventManager.connect()
        curs = db.cursor()
        delcmd = "delete from alert_state where %s" % self.sqlwhere()
        log.debug("clear alert state '%s'", delcmd)
        curs.execute(delcmd)
        db.close()


    def sqlwhere(self):
        """Return sql where to select alert_state data for this event.
        """
        return "userid = '%s' and rule = '%s'" % (self.getUserid(), self.id)


InitializeClass(ActionRule)
