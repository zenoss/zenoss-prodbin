###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest

import pkg_resources # Import this so zenoss.protocols will be found
from zenoss.protocols.jsonformat import from_dict
from Products.ZenEvents.events2.proxy import ZepRawEventProxy, EventProxy
from zenoss.protocols.protobufs.zep_pb2 import (EventSummary, Event, EventNote, EventSummaryUpdate,
    EventSort, EventSummaryUpdateRequest, EventSummaryRequest, EventQuery, EventDetailSet, ZepRawEvent)

class EventProxyTagsAndDetailsTest(unittest.TestCase):
    initialEvent = {
    }

    def _countTags(self, event):
        count = 0
        for event_tag in event.tags:
            count += len(event_tag.uuid)
        return count

    def test_0_TagUpdates(self):
        eventproto = from_dict(ZepRawEvent, self.initialEvent)
        proxy = ZepRawEventProxy(eventproto)

        proxy.tags.addAll('TAG_TYPE_1', ['value%d' % i for i in range(10)])
        proxy.tags.addAll('TAG_TYPE_2', ['value0',])
        proxy.tags.addAll('TAG_TYPE_3', ['value0', 'value1'])
        self.assertEqual(self._countTags(eventproto.event), 13)

        proxy.tags.clearType('TAG_TYPE_1')
        self.assertEqual(self._countTags(eventproto.event), 3)

        self.assertEqual(len(proxy.tags.getByType('TAG_TYPE_3')), 2)

        proxy.tags.clearType('TAG_TYPE_3')
        self.assertEquals(self._countTags(eventproto.event), 1)
        self.assertEqual(len(proxy.tags.getByType('TAG_TYPE_2')), 1)

    def test_1_DetailUpdates(self):
        eventproto = from_dict(Event, self.initialEvent)
        proxy = EventProxy(eventproto)

        proxy.details['A'] = 1000
        proxy.details['B'] = (1000,)

        self.assertEqual(len(proxy.details), 2)
        self.assertEqual(proxy.details['A'], '1000')
        self.assertRaises(KeyError, proxy.details.__getitem__, 'C')
        del proxy.details['B']
        self.assertEqual(len(proxy.details), 1)
        self.assertRaises(KeyError, proxy.details.__getitem__, 'B')
        # but this does not raise a KeyError
        del proxy.details['B']
        del proxy.details['A']
        self.assertEqual(len(proxy.details), 0)

if __name__ == '__main__':
    unittest.main()
