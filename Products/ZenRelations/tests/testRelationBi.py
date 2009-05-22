###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os, sys
if __name__ == '__main__':
  execfile(os.path.join(sys.path[0], 'framework.py'))

from Acquisition import aq_base
from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.ToOneRelationship import ToOneRelationship

from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.PerformanceConf import manage_addPerformanceConf

from Products.ZenRelations.Exceptions import *


class TestRelationBi(ZenModelBaseTest):

    def testThingy(self):


        def _remoteRemove(self, obj=None):
            """
            Copied code from ToOneRelationship, plus a raise to make sure it
            stops breaking the relationship.
            """
            if self.obj:
                if obj != None and obj != self.obj: raise ObjectNotFound
                remoteRel = getattr(aq_base(self.obj), self.remoteName())

                # Here's the extra line
                raise ObjectNotFound('THIS IS A FAKE ERROR')

                remoteRel._remove(self.__primary_parent__)
        # Monkeypatch
        ToOneRelationship._remoteRemove = _remoteRemove

        test = self.dmd.Devices.createOrganizer('test')
        test2 = self.dmd.Devices.createOrganizer('test2')
        dev = test.createInstance('dev')

        dev.setPerformanceMonitor('collector')

        collector = self.dmd.Monitors.getPerformanceMonitor('collector')

        self.assertEqual(len(collector.devices()), 1)

        def succeedsWithoutError(callable, *args, **kwargs):
            try:
                callable(*args, **kwargs)
            except:
                return False
            return True

        # Control: Make sure the collector-device relationship is ok
        self.assert_(succeedsWithoutError(collector.getDevices))

        # Delete the device
        dev.deleteDevice()

        # Make sure the collector-device relationship is all clean
        self.assert_(succeedsWithoutError(collector.getDevices))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRelationBi))
    return suite


if __name__ == '__main__':
    framework()
