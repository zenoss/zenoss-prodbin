##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from mock import Mock

from Products.ZenHub.interfaces import ICollectorEventTransformer, \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP

from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenEvents.SyslogMsgFilter import SyslogMsgFilter
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class SyslogMsgFilterTest(BaseTestCase):

    def testSyslogMsgDefaultFilter(self):
        # Currently there are not any default filters defined
        msgFilter = SyslogMsgFilter()
        msgFilter._daemon = Mock()
        msgFilter._eventService = Mock()
        msgFilter._initialized = True
        msgFilter.updateRuleSet(EventManagerBase.syslogMsgEvtFieldFilterRules)
        self.assertEquals(msgFilter._eventService.sendEvent.called, False)

    def testSyslogMsgBadCfg(self):
        filterCfg = {
            "eventClassKey": [
                "(BadBad"
            ]
        }
        msgFilter = SyslogMsgFilter()
        msgFilter._daemon = Mock()
        msgFilter._eventService = Mock()
        msgFilter._initialized = True
        msgFilter.updateRuleSet(filterCfg)
        self.assertEquals(msgFilter._eventService.sendEvent.called, True)
        self.assertEquals(msgFilter._eventService.sendEvent.call_count, 1)
        evtFields = msgFilter._eventService.sendEvent.mock_calls[0][1][0]
        self.assertEquals(
            evtFields['message'],
            "Syslog Message Filter configuration for the 'eventClassKey' event field could not compile rule #0 with the expression of '(BadBad'. Error error('unbalanced parenthesis',)"
        )

    def testSyslogMsgFilterMatch(self):
        filterCfg = {
            "eventClassKey": [
                "MARK"
            ]
        }
        event = {
            'severity': 4,
            'eventClassKey': 'MARK',
            'component': 'zensyslog',
            'summary': 'test message',
            'eventKey': 'SyslogMessageFilter.eventClassKey.0',
            'device': '127.0.0.1',
            'eventClass': '/App/Zenoss',
            'message': 'test test 123'
        }
        msgFilter = SyslogMsgFilter()
        msgFilter._daemon = Mock()
        msgFilter._daemon.counters = {
            'eventCount': 0,
            'eventFilterDroppedCount': 0}
        msgFilter._eventService = Mock()
        msgFilter._initialized = True
        msgFilter.updateRuleSet(filterCfg)
        self.assertEquals(msgFilter._eventService.sendEvent.called, False)
        transformResult = msgFilter.transform(event)
        self.assertEquals(transformResult, TRANSFORM_DROP)
        event['eventClassKey'] = "NotMark"
        transformResult = msgFilter.transform(event)
        self.assertEquals(transformResult, TRANSFORM_CONTINUE)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(SyslogMsgFilterTest))
    return suite