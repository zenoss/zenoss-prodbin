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

    def test_log(self):
        evid = self.sendEvent()
        detail = self.svc.detail(evid)
        self.assert_(not detail['log'])
        self.svc.log(evid, 'this is a message')
        detail = self.svc.detail(evid)
        self.assert_(detail['log'])

    def test_create(self):

        _notified = []
        @zope.component.adapter(IEventAdded)
        def _evadded(event):
            _notified.append(event)
        zope.component.provideHandler(_evadded)

        evid = self.svc.create(summary='test_create test event', severity=4,
                          device='localhost')

        # Make sure notification occurred
        self.assertEqual(len(_notified), 1)

        # Make sure we get back a valid event id
        self.assert_(evid)
        self.assert_(isinstance(evid, basestring))
        self.assertEqual(len(self.svc.query(filters={'evid':evid})['events']), 1)

        # We created event outside the layer, so let it get cleaned up
        self.layer._evids.append(evid)

    def test_query(self):

        # Test that it returns the correct thing
        result = self.svc.query()
        self.assert_(isinstance(result, dict))
        self.assertEqual(len(result.keys()), 3)
        self.assert_('total' in result)
        self.assert_('events' in result)
        self.assert_('data' in result)

        # Store total so we can take it into account later
        orig_total = result['total']

        # Send an event and make sure it picks it up
        evids = [ev.evid for ev in result['events']]
        evid = self.sendEvent(summary='Zuul Test Event 0')
        # Double-check that it's a new event
        self.assert_(evid not in (ev.evid for ev in result['events']))
        # Get some new results and see if the new event is there
        result = self.svc.query()
        # Make sure events are the right type
        from Products.ZenEvents.ZEvent import ZEvent
        self.assert_(isinstance(result['events'][0], ZEvent))
        # Make sure we picked up the event
        self.assert_(result['events'])
        self.assert_(evid in (ev.evid for ev in result['events']))

        # Test bad values for start and limit
        self.svc.query(start=-1)
        self.svc.query(limit=-1)

        # Pick a number of rows and a start other than 0 and make sure we get
        # the right number of events
        for i in range(1,6):
            self.sendEvent(summary='Zuul Test Event %s' % i)
        total = orig_total + 6
        evs = self.svc.query(start=0, limit=5)['events']
        self.assertEqual(len(evs), 5)
        evs = self.svc.query(start=total-3, limit=5)['events']
        self.assertEqual(len(evs), 3)

        # Try filtering by summary
        evs = self.svc.query(filters={'summary':'Zuul Test Event'})
        self.assertEqual(evs['total'], 6)

        # Test sorting in both dirs
        summaries = ['Zuul Test Event %s' % i for i in range(6)]
        evs = self.svc.query(filters={'summary':'Zuul Test Event'},
                       sort='summary',
                       dir='ASC')['events']
        self.assertEqual(summaries, [ev.summary for ev in evs])
        evs = self.svc.query(filters={'summary':'Zuul Test Event'},
                       sort='summary',
                       dir='DESC')['events']
        summaries.reverse()
        self.assertEqual(summaries, [ev.summary for ev in evs])

    def test_acknowledge(self):
        evid = self.sendEvent(summary="Testing acknowledge")
        event = self.getEvent(evid)
        self.assertEqual(event.eventState, 0)
        self.svc.acknowledge(evids=(evid,))
        event = self.getEvent(evid)
        self.assertEqual(event.eventState, 1)

    def test_unacknowledge(self):
        _notified = []
        @zope.component.adapter(IEventUnacknowledged)
        def _evunacked(event):
            _notified.append(event)
        zope.component.provideHandler(_evunacked)
        evid = self.sendEvent(summary="Testing unacknowledge")
        self.svc.acknowledge(evids=(evid,))
        event = self.getEvent(evid)
        self.assertEqual(event.eventState, 1)
        self.svc.unacknowledge(evids=(evid,))
        event = self.getEvent(evid)
        self.assertEqual(event.eventState, 0)
        self.assertEqual(len(_notified), 1)

    def test_close(self):
        _notified = []
        @zope.component.adapter(IEventClosed)
        def _evclosed(event):
            _notified.append(event)
        zope.component.provideHandler(_evclosed)
        evid = self.sendEvent(summary="Testing reopen")
        event = self.getEvent(evid)
        self.assertEqual(event.eventState, 0)
        self.svc.close(evids=(evid,))
        event = self.getEvent(evid)
        self.assert_(event is None)
        self.assertEqual(len(_notified), 1)

    def test_reopen(self):
        _notified = []
        @zope.component.adapter(IEventReopened)
        def _evreopened(event):
            _notified.append(event)
        zope.component.provideHandler(_evreopened)
        evid = self.sendEvent(summary="Testing reopen")
        self.svc.close(evids=(evid,))
        event = self.getEvent(evid)
        self.assert_(event is None)
        self.svc.reopen(evids=(evid,))
        event = self.getEvent(evid)
        self.assert_(event is not None)
        self.assertEqual(event.eventState, 0)
        self.assertEqual(len(_notified), 1)



def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestEvents),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
