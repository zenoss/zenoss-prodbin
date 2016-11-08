##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import Globals

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.EventClassInst import EventClassInst


class testEventClassInst(BaseTestCase):
    def afterSetUp(self):
        super(testEventClassInst, self).afterSetUp()

        self.testEvents = [EventClassInst('testEvents')
                           for i in range(10)]
        for i, event in enumerate(self.testEvents):
            event.sequence = i
            event.sameKey = lambda: self.testEvents


    def testUpdatePropertyNoDuplicates(self):
        for i, event in enumerate(self.testEvents):
            event.sequence = i

        for i, event in enumerate(self.testEvents):
            if i == 0:
                continue
            self.assertRaises(ValueError,
                              event._updateProperty, 'sequence', 0)

        for i, event in enumerate(self.testEvents):
            self.assertEqual(event.sequence, i)


    def testUpdateProperty(self):
        for i, event in enumerate(self.testEvents):
            event.sequence = i

        for i, event in enumerate(self.testEvents):
            event._updateProperty('sequence', event.sequence + 100)

        for i, event in enumerate(self.testEvents):
            self.assertEqual(event.sequence, i + 100)
