###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from ZODB.transact import transact

import copy
import re
import sre_constants
import logging
import transaction
from Products.ZenMessaging.audit import audit

log = logging.getLogger("zen.Events")

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_chain
from zope.interface import implements

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.EventView import EventView
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenWidgets import messaging
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenUtils.Utils import convToUnits, zdecode, getDisplayName
from Products.ZenUtils.Time import SaveMessage
from Products import Zuul
from Products.Zuul.interfaces import IInfo


def manage_addEventClassInst(context, id, REQUEST = None):
    """make a device class"""
    dc = EventClassInst(id)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


class EventClassPropertyMixin(object):

    transform = ''

    _properties = (
        {'id':'transform', 'type':'text', 'mode':'w'},
        )

    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Any non-None property values are applied to the event.
        """
        evt._clearClasses = copy.copy(getattr(self, "zEventClearClasses", []))
        evt._action = getattr(self, "zEventAction", "status")
        sev = getattr(self, "zEventSeverity", -1)
        if sev >= 0:
            if evt.severity > 0:
                evt.severity = sev
        log.debug("Per transform/mapping, using severity %s, action '%s' and clear classes %s",
                  evt.severity, evt._action, evt._clearClasses)
        updates = {}
        for name in 'resolution', 'explanation':
            value = getattr(self, name, None)
            if value is not None and value != '':
                updates[name] = value
        if updates:
            log.debug("Adding fields from transform/mapping: %s", updates)
        evt.updateFromDict(updates)
        return evt

    def formatTransform(self, transformLines):
        """
        Convenience function to number the transform info
        """
        return '\n'.join("%3s %s" % enumText
                         for enumText in enumerate(transformLines))

    def sendTransformException(self, eventclass, evt):
        """
        Try to convert the rather horrible looking traceback that
        is hard to understand into something actionable by the user.
        """
        transformName = '/%s'% '/'.join(eventclass.getPhysicalPath()[4:])
        summary = "Error processing transform/mapping on Event Class %s" % \
            transformName

        import sys
        from traceback import format_exc, extract_tb
        tb = extract_tb(sys.exc_info()[2])
        exceptionText = format_exc(0).splitlines()[1]

        transformLines = eventclass.transform.splitlines()
        transformFormatted = self.formatTransform(transformLines)

        # try to extract line number and code from traceback, but set up
        # default values in case this fails - don't want to throw a traceback
        # when cleaning up a traceback
        badLineNo = None
        badLineText = ''
        try:
            # if tb has only 1 entry, then the transform didn't compile/run at all
            if len(tb) > 1:
                # runtime error, get line number from last entry in traceback
                # (subtract 1, since traceback numbering is 1-based)
                badLineNo = tb[-1][1] - 1
                badLineText = transformLines[badLineNo]
            else:
                # assume compile error, with exceptionText in the form:
                # '  File "<string>", line 4'
                badLineText = "<transform failed to compile>>"
                badLineNo = int(exceptionText.rsplit(None,1)[1]) - 1
                badLineText = transformLines[badLineNo]
                exceptionText = "compile error on line %d" % badLineNo
        except Exception:
            pass

        message = """%s
Problem on line %s: %s
%s

Transform:
%s
""" % (summary, badLineNo, exceptionText, badLineText,
        transformFormatted)
        log.warn(message)

        # Now send an event
        zem = self.getDmd().ZenEventManager
        badEvt = dict(
            dedupid='|'.join([transformName,zem.host]),
            # Don't send the *same* event class or we trash and
            # and crash endlessly
            eventClass='/',
            device=zem.host,
            component=transformName,
            summary=summary,
            severity=4,
            message = "Problem with line %s: %s" % (badLineNo, badLineText),
            transform=transformFormatted,
            exception=exceptionText,
        )
        zem.sendEvent(badEvt)

    def applyTransform(self, evt, device, component=None):
        """
        Apply transforms on an event from the top level of the Event Class Tree
        down to the actual Event Rules (EventClassInst)
        """
        transpath = self._eventClassPath()
        variables_and_funcs = {
            'evt':evt, 'device':device, 'dev':device,
            'convToUnits':convToUnits, 'zdecode':zdecode,
            'txnCommit':transaction.commit,  # this function is deprecated in favor of transforms using @transact
            'transact':transact, 'dmd':self.dmd,
            'log':log, 'component':component,
            'getFacade':Zuul.getFacade, 'IInfo':IInfo,
        }
        for eventclass in transpath:
            if not eventclass.transform: continue
            try:
                log.debug('Applying transform/mapping at Event Class %s',
                    eventclass.getPrimaryDmdId())
                exec(eventclass.transform, variables_and_funcs)
                log.debug('Results after transform: %s',
                          variables_and_funcs['evt'])
            except Exception, ex:
                self.sendTransformException(eventclass, evt)

        return variables_and_funcs['evt']


    def inheritedTransforms(self):
        """
        Make a string that brings together all the transforms inherited from the
        base EventClass to self.
        """
        transpath = self._eventClassPath()
        transtext = []
        for obj in transpath:
            if not obj.transform: continue
            if obj.transform == self.transform: break
            transtext.append("""<a href='%s/editEventClassTransform'>%s<a>
                """ % (obj.getPrimaryUrlPath(), obj.getPrimaryDmdId()))
            transtext.append("<pre>%s</pre>" % obj.transform)
        return "\n".join(transtext)


    def testTransformStyle(self):
        """Test our transform by compiling it.
        """
        try:
            if self.transform:
                compile(self.transform, "<string>", "exec")
        except:
            return "color:#FF0000;"


    def _eventClassPath(self):
        """
        Return the path to our current EventClassInst from the top level
        EventClass down. We use this to process and display the heirarchy of
        event transforms.
        """
        transpath = []
        for obj in aq_chain(self):
            # skip over relationships in the aq_chain
            if not isinstance(obj, EventClassPropertyMixin): continue
            if obj.id == 'dmd': break
            transpath.append(obj)
        transpath.reverse()
        return transpath

# Why is this a subclass of EventView?

class EventClassInst(EventClassPropertyMixin, ZenModelRM, EventView,
                     ZenPackable):
    """
    EventClassInst.
    """
    implements(IIndexed, IGloballyIdentifiable)

    event_key = meta_type = "EventClassInst"

    default_catalog = "eventClassSearch"

    actions = ("status", "history", "heartbeat", "drop")

    _properties = EventClassPropertyMixin._properties + (
        {'id':'eventClassKey', 'type':'string', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'rule', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        {'id':'explanation', 'type':'text', 'mode':'w'},
        {'id':'resolution', 'type':'text', 'mode':'w'},
        )


    _relations = ZenPackable._relations + (
        ("eventClass", ToOne(ToManyCont,"Products.ZenEvents.EventClass","instances")),
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
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEditNew'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
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
        return EventView.getStatus(self, self.getEventClass())

    def getEventClass(self):
        """Return the full EventClass of this EventClassInst."""
        return self.getOrganizerName()

    def getEventClassHref(self):
        """Return href of our class.
        """
        return self.eventClass().getPrimaryUrlPath()


    def getDmdKey(self):
        """Return the dmd key of this mapping ie: /App/Start/zentinel
        """
        return self.getOrganizerName() + "/" + self.id


    def applyExtraction(self, evt):
        """
        Apply the event dict regex to extract additional values from the event.
        """
        if self.regex:
            m = re.search(self.regex, evt.message)
            if m: evt.updateFromDict(m.groupdict())
        return evt


    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Any non-None property values are applied to the event.
        """
        evt.eventClass = self.getEventClass()
        evt.eventClassMapping = '%s/%s' % (self.getEventClass(), self.id)
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


    def match(self, evt, device):
        """
        Match an event message against our regex.

        @parameter evt: event to match in our mapping
        @type evt: dictionary
        @parameter device: device
        @type device: DMD object
        @return: boolean
        @rtype: boolean
        """
        value = False
        log.debug("match on:%s", self.getPrimaryDmdId())
        if self.rule:
            try:
                log.debug("eval rule:%s", self.rule)
                value = eval(self.rule, {'evt':evt, 'dev':device, 'device': device})
            except Exception, e:
                logging.warn("EventClassInst: %s rule failure: %s",
                            self.getDmdKey(), e)
        else:
            try:
                log.debug("regex='%s' message='%s'", self.regex, evt.message)
                value = re.search(self.regex, evt.message, re.I)
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
        return [ i for i in self.eventClass().find(self.eventClassKey) \
            if i.eventClassKey == self.eventClassKey ]


    security.declareProtected('Manage DMD', 'manage_resequence')
    def manage_resequence(self, seqmap, REQUEST=None):
        """Reorder the sequence of eventClassMappings with the same key.
        """
        # first pass set new sequence
        for i, map in enumerate(self.sameKey()):
            map.sequence = int(seqmap[i])
        # second pass take out any holes
        for i, map in enumerate(self.sameKey()):
            map.sequence = i
        if REQUEST:
            audit('UI.EventClassMapping.Resequence', self.id, sequence=seqmap)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_editEventClassInst')
    def manage_editEventClassInst(self, name='', eventClassKey='',
                                regex='', rule='', example='',
                                transform='',
                                explanation='', resolution='', REQUEST=None):
        """Edit an EventClassInst from a web page."""

        #save arguments for audit logging
        values = locals()

        oldValues = {
            'name':getDisplayName(self),
            'eventClassKey':self.eventClassKey,
            'regex':self.regex,
            'rule':self.rule,
            'example':self.example,
            'transform':self.transform,
            'explanation':self.explanation,
            'resolution':self.resolution,
        }
        
        redirect = self.rename(name)
        if eventClassKey and self.eventClassKey != eventClassKey:
            self.unindex_object()
            self.sequence = self.eventClass().nextSequenceNumber(eventClassKey)
            self.eventClassKey = eventClassKey
            self.index_object()
        self.regex = regex
        self.rule = rule
        self.example = example
        self.transform = transform
        self.explanation = explanation
        self.resolution = resolution
        if REQUEST:
            audit('UI.EventClassMapping.Edit', self, data_=values, oldData_=oldValues, skipFields_=['self','REQUEST'])
            messaging.IMessageSender(self).sendToBrowser(
                'Saved', SaveMessage())
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(EventClassInst)
