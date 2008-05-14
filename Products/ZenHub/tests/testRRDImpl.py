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

import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestRRDImpl(BaseTestCase):

    def createRRDFile(self, path):
        import rrdtool
        rrdtool.create(zenPath('perf/Devices/ds_dp.rrd'),
                       '--step=1',
                       'DS:ds0:GAUGE',
                       'RRA:AVERAGE')

    def testRRDImpl(self):
        from Products.ZenHub.services.RRDImpl import RRDImpl
        from Products.ZenModel.Device import manage_createDevice
        d = manage_createDevice(self.dmd,
                                deviceName='127.0.0.1',
                                devicePath='/Test')
        from Products.ZenModel.RRDTemplate import manage_addRRDTemplate
        manage_addRRDTemplate(self.dmd.Devices.Test.rrdTemplates, 'Device')
        t = self.dmd.Devices.Test.rrdTemplates.Device
        ds = t.manage_addRRDDataSource('ds', 'BasicDataSource.COMMAND')
        dp = ds.manage_addRRDDataPoint('dp')
        thresh = t.manage_addRRDThreshold('limit', 'MinMaxThreshold')
        thresh.maxval = "100"
        thresh.dsnames = ('ds_dp',)
        impl = RRDImpl(self.dmd)
        evts = []
        def append(evt):
            if evt['severity'] != 0:
                evts.append(evt)
        impl.zem.sendEvent = append
        impl.writeRRD(d.id, '', '', 'ds_dp', 99)
        self.assert_(len(evts) == 0)
        impl.writeRRD(d.id, '', '', 'ds_dp', 101)
        self.assert_(len(evts) != 0)
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRRDImpl))
    return suite
