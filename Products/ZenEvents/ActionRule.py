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
import time
import re
from sets import Set
import logging
log = logging.getLogger("zen.ActionRule")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import * 
from Acquisition import aq_parent

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenEvents.EventFilter import EventFilter
from Products.ZenWidgets import messaging

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
    repeatTime = 0
    action = "email"
    format = "[zenoss] %(device)s %(summary)s"
    body =  "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
            "Time: %(firstTime)s\n" \
            "Message:\n%(message)s\n" \
            "<a href=\"%(eventUrl)s\">Event Detail</a>\n" \
            "<a href=\"%(ackUrl)s\">Acknowledge</a>\n" \
            "<a href=\"%(deleteUrl)s\">Delete</a>\n" \
            "<a href=\"%(eventsUrl)s\">Device Events</a>\n"
    sendClear = True
    clearFormat = "[zenoss] CLEAR: %(device)s %(clearOrEventSummary)s"
    clearBody =  \
            "Event: '%(summary)s'\n" \
            "Cleared by: '%(clearSummary)s'\n" \
            "At: %(clearFirstTime)s\n" \
            "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severityString)s\n" \
            "Message:\n%(message)s\n" \
            "<a href=\"%(undeleteUrl)s\">Undelete</a>\n"
    enabled = False
    actionTypes = ("page", "email") 
    targetAddr = ""
    plainText = False

    _properties = ZenModelRM._properties + (
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'format', 'type':'text', 'mode':'w'},
        {'id':'body', 'type':'text', 'mode':'w'},
        {'id':'sendClear', 'type':'boolean', 'mode':'w'},
        {'id':'clearFormat', 'type':'text', 'mode':'w'},
        {'id':'clearBody', 'type':'text', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'action', 'type':'selection', 'mode':'w',
            'select_variable': 'actionTypes',},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'targetAddr', 'type':'string', 'mode':'w'},
        {'id':'repeatTime', 'type':'int', 'mode':'w'},
        {'id':'plainText', 'type':'boolean', 'mode':'w'},
    )

    _relations = (
        ("windows", ToManyCont(ToOne,"Products.ZenEvents.ActionRuleWindow","actionRule")),
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
                , 'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                },
                { 'id'            : 'message'
                , 'name'          : 'Message'
                , 'action'        : 'editActionRuleMessage'
                , 'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                },
                { 'id'            : 'schedule'
                , 'name'          : 'Schedule'
                , 'action'        : 'editActionRuleSchedule'
                , 'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
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
        result.update([ f for f in re.findall("%\((\S+)\)s", self.clearFormat) \
            if not f.startswith('clear') ])
        result.update([ f for f in re.findall("%\((\S+)\)s", self.clearBody) \
            if not f.startswith('clear') ])
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearFormat)))
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearBody)))
        notDb = Set('orEventSummary eventUrl eventsUrl ackUrl deleteUrl undeleteUrl severityString'.split())
        notMsg = ['severity', 'summary']
        return list(result - notDb) + notMsg


    def checkFormat(self):
        """Check that the format string has valid fields.
        """
        evtfields = self.dmd.ZenEventManager.getFieldList()
        for field in self.getEventFields():
            if field not in evtfields:
                return False
        return True


    def getAddresses(self):
        """Return the correct addresses for the action this rule uses.
        """
        if self.targetAddr:
            return [self.targetAddr]
        elif self.action == "page":
            return self.getUser().getPagerAddresses()
        elif self.action == "email":
            return self.getUser().getEmailAddresses()


    def getUser(self):
        """Return the user this action is for.
        """
        return self.getPrimaryParent()

    def getUserid(self):
        """Return the userid this action is for.
        """
        return self.getUser().getId()

    
    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editActionRule')
    def manage_editActionRule(self, REQUEST=None):
        """Update user settings.
        """
        if not self.enabled:
            self._clearAlertState()
        import WhereClause
        if REQUEST.form.has_key('onRulePage') \
                and not REQUEST.form.has_key('where'):
            clause = WhereClause.fromFormVariables(self.genMeta(), REQUEST.form)
            if clause:
                REQUEST.form['where'] = clause
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Invalid',
                    'An alerting rule must have at least one criterion.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        return self.zmanage_editProperties(REQUEST)


    def _clearAlertState(self):
        """Clear state in alert_state before we are deleted.
        """
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            delcmd = "delete from alert_state where %s" % self.sqlwhere()
            log.debug("clear alert state '%s'", delcmd)
            curs = conn.cursor()
            curs.execute(delcmd)
        finally: zem.close(conn)

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

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES,
                              'manage_addActionRuleWindow')
    def manage_addActionRuleWindow(self, newId, REQUEST=None):
        "Add a ActionRule Window to this device"
        if newId:
            mw = ActionRuleWindow(newId)
            self.windows._setObject(newId, mw)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Active Period Added',
                'The action rule window has been created successfully.'
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES,
                              'manage_deleteActionRuleWindow')
    def manage_deleteActionRuleWindow(self, windowIds, REQUEST=None):
        "Delete a ActionRule Window to this device"
        import types
        if type(windowIds) in types.StringTypes:
            windowIds = [windowIds]
        for id in windowIds:
            self.windows._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Active Period Deleted',
                'The action rule window has been removed.'
            )
            return self.callZenScreen(REQUEST)


InitializeClass(ActionRule)
