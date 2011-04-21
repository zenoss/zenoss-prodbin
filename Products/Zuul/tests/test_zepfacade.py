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
import zope.component.event
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.ZenUtils.guid import generate
from Products.Zuul.interfaces import *
from Products.Zuul import getFacade
from Products.ZenEvents.ZenEventClasses import Unknown


class TestZepFacade(ZuulFacadeTestCase):

    def setUp(self):
        super(TestZepFacade, self).setUp()
        self.eventClassId = "App"
        self.dmd.Events.createOrganizer(self.eventClassId)
        self.zep = getFacade('zep', self.dmd)

    def test_interfaces(self):
        pass

    def test_create_event_mapping(self):
        eventdata = [dict(eventClassKey="abc123",
                          evid = generate(),
                          eventClass={'text': Unknown})]
        msg, url = self.zep.createEventMapping(eventdata, "/" + self.eventClassId)
        # verify the msg
        self.assertTrue('Created 1 event mapping' in msg)

    def test_invalid_event_class(self):
        eventdata = [dict(eventClassKey="abc1234",
                          evid = generate(),
                          eventClass={'text': "/Pepe"})]
        msg, url = self.zep.createEventMapping(eventdata, "/" + self.eventClassId)
        # verify the msg
        self.assertTrue('is not of the class Unknown' in msg)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestZepFacade),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
