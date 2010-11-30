###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import zope.component
import zope.component.event
from zope.interface.verify import verifyClass
from Products.ZenModel.DataRoot import DataRoot
from Products.Zuul.tests.base import EventTestCase, ZuulFacadeTestCase
from Products.Zuul.interfaces import *
from Products.Zuul.facades.eventfacade import EventFacade
from Products.Zuul import getFacade
from Products.Zuul.facades import eventfacade as evs
from Products.Zuul.infos.event import EventInfo

class TestEvents(EventTestCase, ZuulFacadeTestCase):

    def setUp(self):
        super(TestEvents, self).setUp()
        self.svc = getFacade('event', self.dmd)

    def _run_query(self, query):
        zem = self.svc._event_manager(history=False)
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute(query)
            return curs.fetchall()
        finally:
            zem.close(conn)

    def getEvent(self, evid):
        try:
            return self.svc.query(filters={'evid':evid})['events'][0]
        except IndexError:
            return None

    def test_event_manager(self):
        zem = self.svc._event_manager(history=False)
        zhm = self.svc._event_manager(history=True)
        self.assertEqual(zem.id, 'ZenEventManager')
        self.assertEqual(zhm.id, 'ZenEventHistory')

    def test_interfaces(self):
        verifyClass(IEventEvent, evs.EventEvent)
        verifyClass(IEventFacade, evs.EventFacade)
        verifyClass(IEventAcknowledged, evs.EventAcknowledged)
        verifyClass(IEventUnacknowledged, evs.EventUnacknowledged)
        verifyClass(IEventAdded, evs.EventAdded)
        verifyClass(IEventClosed, evs.EventClosed)
        verifyClass(IEventReopened, evs.EventReopened)
        verifyClass(IEventInfo, EventInfo)

    def test_registration(self):
        svc = self.svc
        self.assertEqual(svc.__class__, EventFacade)
        self.assert_(isinstance(svc._dmd, DataRoot))

    def test_fields(self):
        fields = self.dmd.ZenEventManager.defaultResultFields
        self.assertEqual(self.svc.fields(), fields)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestEvents),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
