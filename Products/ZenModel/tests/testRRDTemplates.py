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

from ZenModelBaseTest import ZenModelBaseTest

class TestRRDTemplates(ZenModelBaseTest):

    def testCatalogExists(self):
        catalog = getattr(self.dmd, 'searchRRDTemplates', None)
        self.assert_(catalog is not None)

    def testBackwardCompatible(self):
        getid = lambda x:x.id
        ts1 = map(getid, self.dmd.Devices.getAllRRDTemplates())
        ts2 = map(getid, self.dmd.Devices.getAllRRDTemplatesPainfully())
        ts1.sort(); ts2.sort()
        self.assertEqual(ts1, ts2)

    def testFallBackToPainful(self):
        cattemplates = self.dmd.Devices.getAllRRDTemplates()

        self.dmd._delObject('searchRRDTemplates')
        self.assert_(getattr(self.dmd, 'searchRRDTemplates', None) is None)

        templates = self.dmd.Devices.getAllRRDTemplates()
        templates2 = self.dmd.Devices.getAllRRDTemplatesPainfully()

        cattemplates.sort(); templates.sort(); templates2.sort()
        self.assertEqual(templates, templates2)
        self.assertEqual(cattemplates, templates2)
        self.assertEqual(cattemplates, templates)

    def testTemplateRetrieval(self):
        devices = self.dmd.Devices
        server = self.dmd.Devices.createOrganizer('/Server')
        linux = self.dmd.Devices.createOrganizer('/Server/Linux')

        devices.manage_addRRDTemplate('test1')
        server.manage_addRRDTemplate('test2')
        linux.manage_addRRDTemplate('test3')

        getid = lambda x:x.id
        devtemps = map(getid, devices.getAllRRDTemplates())
        sertemps = map(getid, server.getAllRRDTemplates())
        lintemps = map(getid, linux.getAllRRDTemplates())

        self.assert_('test1' in devtemps)
        self.assert_('test2' in devtemps)
        self.assert_('test3' in devtemps)

        self.assert_('test1' not in sertemps)
        self.assert_('test2' in sertemps)
        self.assert_('test3' in sertemps)

        self.assert_('test1' not in lintemps)
        self.assert_('test2' not in lintemps)
        self.assert_('test3' in lintemps)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRRDTemplates))
    return suite

if __name__=="__main__":
    framework()
