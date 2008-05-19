###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from unittest import TestSuite, makeSuite, TestCase

from Products.ZenEvents.SyslogProcessing import SyslogProcessor

class SyslogProcessingTest(TestCase):
    "FIXME: add more tests"

    def sendEvent(self, evt):
        self.sent = evt

    def testBuildEventClassKey(self):
        "Simple, brain-dead testing of SyslogProcessor"
        base = dict(device='localhost', component='component', severity=3)
        s = SyslogProcessor(self.sendEvent, 6, False, 'localhost', 3)
        self.assert_(s.buildEventClassKey({}) == {})
        evt = dict(eventClassKey='akey', **base)
        self.assert_(s.buildEventClassKey(evt.copy()) == evt)
        evt = dict(eventClassKey='akey', ntevid='1234', **base)
        self.assert_(s.buildEventClassKey(evt.copy()) == evt)
        evt = dict(ntevid='1234', **base)
        self.assert_(s.buildEventClassKey(evt)['eventClassKey'] ==
                     'component_1234')
        evt = dict(**base)
        self.assert_(s.buildEventClassKey(evt)['eventClassKey'] == 'component')


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SyslogProcessingTest))
    return suite
