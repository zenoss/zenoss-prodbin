###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import zope.component
from Products.Five import zcml
import Products.ZenTestCase
from zope.traversing.adapters import DefaultTraversable
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenTestCase.BaseTestCase import ZenossTestCaseLayer
from Products.ZenEvents.Event import Event
from Products.ZenUtils.ZCmdBase import ZCmdBase

from itertools import count
counter = count()

class FakeAdaptee(object):
    def __init__(self):
        self._p_oid = counter.next()

class FakeInfo(object):
    def __init__(self):
        self._object = FakeAdaptee()


class ZuulFacadeTestCase(BaseTestCase):
    def test_interfaces(self):
        raise NotImplementedError("You're not verifying that the"
                                  " class correctly implements its"
                                  " interfaces.")

class EventTestLayer(ZenossTestCaseLayer):

    _evids = None

    @classmethod
    def setUp(cls):
        zope.component.testing.setUp(cls)
        zope.component.provideAdapter(DefaultTraversable, (None,))
        zcml.load_config('testing-noevent.zcml', Products.ZenTestCase)
        zodb = ZCmdBase(noopts=True)
        zem = zodb.dmd.ZenEventManager
        cls.zem = zem
        cls._evids = []

    @classmethod
    def tearDown(cls):
        ZenossTestCaseLayer.tearDown()
        if not cls._evids:
            return
        evids = ','.join("'%s'" % evid for evid in cls._evids)
        conn = cls.zem.connect()
        try:
            curs = conn.cursor()
            curs.execute('DELETE FROM status WHERE evid in (%s)' % evids)
        finally:
            cls.zem.close(conn)

class EventTestCase(unittest.TestCase):

    layer = EventTestLayer

    def sendEvent(self, **kwargs):
        evt = Event()
        defaults = dict(
            device='localhost',
            eventClass="/TestEvent",
            summary='Test event generated by %s' %
                        self.__class__.__name__,
            severity=4)
        defaults.update(kwargs)
        for k,v in defaults.items():
            setattr(evt, k, v)

        evid = self.layer.zem.sendEvent(evt)
        self.layer._evids.append(evid)
        return evid

    def clearCache(self):
        self.layer.zem.clearCache()
        self.layer.zem.manage_clearCache()

