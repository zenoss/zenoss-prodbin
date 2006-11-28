#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import time
import re
from sets import Set
import logging
log = logging.getLogger("zen.ActionRule")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_parent

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenEvents.EventFilter import EventFilter

from ActionRuleWindow import ActionRuleWindow
def _downcase(s):
    return s[0:1].lower() + s[1:]

def manage_addActionRule(context, id, REQUEST=None):
    """Create an action rule"""
    ed = ActionRule(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addActionRule = DTMLFile('dtml/addActionRule',globals())

class ActionRule(ZenModelRM, EventFilter):
    """
    Rule applied to events that then executes an action on matching events.
    """
    
    meta_type = "ActionRule"

    where = "severity >= 4 and eventState = 0 and prodState = 1000"
    delay = 0
    action = "email"
    format = "[zenoss] %(device)s %(summary)s"
    body =  "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
            "Time: %(firstTime)s\n" \
            "Message:\n%(message)s\n" \
            "Event: %(eventUrl)s\n" \
            "Acknowledge: %(ackUrl)s\n" \
            "Delete: %(deleteUrl)s\n" \
            "Device Events: %(eventsUrl)s\n"
    clearFormat = "[zenoss] CLEAR: %(device)s %(clearOrEventSummary)s"
    clearBody =  \
            "Event: '%(summary)s'\n" \
            "Cleared by: '%(clearSummary)s'\n" \
            "At: %(clearFirstTime)s\n" \
            "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
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

    zenRelationsBaseModule = "Products.ZenEvents"
    _relations = (
        ("windows", ToManyCont(ToOne,"ActionRuleWindow","actionRule")),
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
                { 'id'            : 'message'
                , 'name'          : 'Message'
                , 'action'        : 'editActionRuleMessage'
                , 'permissions'   : ("Change Settings",)
                },
                { 'id'            : 'schedule'
                , 'name'          : 'Schedule'
                , 'action'        : 'editActionRuleSchedule'
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
        result = Set()
        result.update(re.findall("%\((\S+)\)s", self.format))
        result.update(re.findall("%\((\S+)\)s", self.body))
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearFormat)))
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearBody)))
        notDb = Set('orEventSummary eventUrl eventsUrl ackUrl deleteUrl severityString'.split())
        return list(result - notDb)


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


    def getUser(self):
        """Return the user this action is for.
        """
        return self.getPrimaryParent()

    def getUserid(self):
        """Return the userid this action is for.
        """
        return self.getUser().getId()

    
    security.declareProtected('Change Settings', 'manage_editActionRule')
    def manage_editActionRule(self, REQUEST=None):
        """Update user settings.
        """
        if not self.enabled:
            self._clearAlertState()
        import WhereClause
        if REQUEST and not REQUEST.form.has_key('where'):
            clause = WhereClause.fromFormVariables(self.genMeta(), REQUEST.form)
            if clause:
                REQUEST.form['where'] = clause
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

    def nextActiveWindow(self):
        next = None
        w = None
        for ar in self.windows():
            if next is None or ar.next() < next:
                next = ar.next()
                w = ar
        return w

    def nextActive(self):
        if self.enabled:
            return time.time()
        w = self.nextActiveWindow()
        if w:
            return w.next()

    def nextActiveNice(self):
        if self.enabled:
            return "Now"
        t = self.nextActive()
        if t is None:
            return "Never"
        return Time.LocalDateTime(t)

    def nextDurationNice(self):
        w = self.nextActiveWindow()
        if w is None:
            return "Forever"
        if self.enabled:
            next = w.next()
            if next:
                return Time.Duration((next + w.duration) - time.time())
        return Time.Duration(w.duration)


    def repeatNice(self):
        w = self.nextActiveWindow()
        if w is None:
            return "Never"
        return w.repeat
        

    security.declareProtected('Change Settings', 'manage_addActionRuleWindow')
    def manage_addActionRuleWindow(self, newId, REQUEST=None):
        "Add a ActionRule Window to this device"
        mw = ActionRuleWindow(newId)
        self.windows._setObject(newId, mw)
        if REQUEST:
            REQUEST['message'] = "Active Period Added"
            return self.callZenScreen(REQUEST)
                          
    security.declareProtected('Change Settings', 'manage_deleteActionRuleWindow')
    def manage_deleteActionRuleWindow(self, windowIds, REQUEST=None):
        "Delete a ActionRule Window to this device"
        import types
        if type(windowIds) in types.StringTypes:
            windowIds = [windowIds]
        for id in windowIds:
            self.windows._delObject(id)
        if REQUEST:
            REQUEST['message'] = "Active Period Deleted"
            return self.callZenScreen(REQUEST)
                          

InitializeClass(ActionRule)
