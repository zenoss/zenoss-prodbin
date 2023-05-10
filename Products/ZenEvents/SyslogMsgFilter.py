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

import zope.interface
import zope.component

from zope.interface import implements

from Products.ZenCollector.interfaces import ICollector, IEventService
from Products.ZenHub.interfaces import ICollectorEventTransformer, \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP
from Products.ZenUtils.Utils import unused, zenPath

log = logging.getLogger("zen.zensyslog.filter")

class SyslogMsgFilterError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message


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
        self._ruleSet = {}

        # TODO ....

    def initialize(self):
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._initialized = True
        log.info('SMA Syslog Message Filter Initialized...')

    def updateRuleSet(self, rules):
        # TODO compile regex'es
        if self._ruleSet != rules:
            log.info('Updating rule-set configuration')
            self._ruleSet = rules

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
            log.info('SMA: transform %r - %r', self._ruleSet, event)
            # TODO, loop through rules


        return result
