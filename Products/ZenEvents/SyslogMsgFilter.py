##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################



__doc__ = """zensyslog

Filters Syslog Messages.
"""

import sys
import logging
import os.path
import re

import zope.interface
import zope.component

from zope.interface import implements

from Products.ZenCollector.interfaces import ICollector, IEventService
from Products.ZenHub.interfaces import ICollectorEventTransformer, \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP
from Products.ZenUtils.Utils import unused, zenPath

log = logging.getLogger("zen.zensyslog.filter")

class SyslogMsgFilter(object):
    implements(ICollectorEventTransformer)
    """
    Interface used to perform filtering of events at the collector. This could be
    used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated for
    the event, so they can set fields which are used by an ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """
    weight = 1
    def __init__(self):
        self._daemon = None
        self._eventService = None
        self._initialized = False
        self._ruleSet = {}

    def initialize(self):
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._initialized = True

    def syslogMsgFilterErrorEvent(self, **kwargs):
        """
        Build an Event dict from parameters.n
        """
        eventDict = {
            'device': '127.0.0.1',
            'eventClass': '/App/Zenoss',
            'severity': 4,
            'eventClassKey': '',
            'summary': 'Syslog Message Filter processing issue',
            'component': 'zensyslog'
        }
        if kwargs:
            eventDict.update(kwargs)
        self._eventService.sendEvent(eventDict)

    def updateRuleSet(self, rules):
        processedRuleSet = {}
        for evtFieldName, evtFieldRules in rules.iteritems():
            if evtFieldName not in processedRuleSet:
                processedRuleSet[evtFieldName] = []
            for i, evtFieldRule in enumerate(evtFieldRules):
                try:
                    compiledRule = re.compile(evtFieldRule, re.DOTALL)
                except Exception as ex:
                    msg = 'Syslog Message Filter configuration for the ' \
                            '{!r} event field could not compile rule #{!r}' \
                            ' with the expression of {!r}. Error {!r}'.format(
                                evtFieldName,
                                i,
                                evtFieldRule,
                                ex)
                    log.warn(msg)
                    self.syslogMsgFilterErrorEvent(
                        message=msg,
                        eventKey="SyslogMessageFilter.{}.{}".format(evtFieldName, i))
                else:
                    processedRuleSet[evtFieldName].append(compiledRule)
        self._ruleSet = processedRuleSet

    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be forwarded on
                 to the next transformer in the sequence, TRANSFORM_STOP if no
                 further transformers should be performed on this event, and
                 TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        result = TRANSFORM_CONTINUE

        if self._daemon and self._ruleSet:
            for evtFieldName, evtFieldRules in self._ruleSet.iteritems():
                if evtFieldName in event:
                    for i, compiledRule in enumerate(evtFieldRules):
                        m = compiledRule.search(event[evtFieldName])
                        if not m:
                            continue
                        else:
                            log.debug(
                                'Syslog Message Filter match! EventFieldName:%r '
                                'EventFieldValue:%r FilterRuleNumber:%s '
                                'FilterRuleExpression:%r',
                                evtFieldName,
                                event[evtFieldName],
                                i,
                                compiledRule.pattern)
                            self._daemon.counters["eventFilterDroppedCount"] += 1
                            return TRANSFORM_DROP
        return result
