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
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.

import os, sys
if __name__ == '__main__':
  execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
import StringIO

from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.tests.dataImportExport import *

from Products.ZenRelations.Exceptions import *

from ZenRelationsBaseTest import ZenRelationsBaseTest

class ExportTest(ZenRelationsBaseTest):

    def testExportObject(self):
        "test exporting rm with properties"
        loc = self.build(self.app, Location, "loc")
        ofile = StringIO.StringIO()
        loc.exportXml(ofile)
        self.assert_(ofile.getvalue() == objnoprops)

    def testExportProperties(self):
        "test exporting rm with properties"
        dev = self.build(self.app, Device, "dev")
        ofile = StringIO.StringIO()
        dev.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithprops)


    def testExportToOne(self):
        "test exporting rm with properties"
        dev = self.build(self.app, Device, "dev")
        loc = self.build(self.app, Location, "loc")
        dev.location.addRelation(loc)
        ofile = StringIO.StringIO()
        dev.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtoone)


    def testExportToMany(self):
        "test exporting rm with properties"
        dev = self.build(self.app, Device, "dev")
        loc = self.build(self.app, Location, "loc")
        dev.location.addRelation(loc)
        ofile = StringIO.StringIO()
        loc.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtomany)


    def testExportToManyCont(self):
        "test exporting rm with properties"
        dev = self.build(self.app, Device, "dev")
        eth0 = self.create(dev.interfaces, IpInterface, "eth0")
        ofile = StringIO.StringIO()
        dev.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtomanycont)


class ImportTest(ZenRelationsBaseTest):
    """Import Tests"""


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ExportTest))
    suite.addTest(makeSuite(ImportTest))
    return suite

if __name__ == '__main__':
    framework()
    #unittest.main()
