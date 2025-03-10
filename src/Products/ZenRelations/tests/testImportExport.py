##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import StringIO
import sys

import six


def _compile_file(filename):
    with open(filename) as f:
        return compile(f.read(), filename, "exec")


if __name__ == "__main__":
    six.exec_(_compile_file(os.path.join(sys.path[0], "framework.py")))


from Products.ZenRelations.Exceptions import *  # noqa F403
from Products.ZenRelations.ImportRM import NoLoginImportRM  # noqa F403

from Products.ZenRelations.tests.dataImportExport import (  # noqa F403
    objnoprops,
    objwithprops,
    objwithskip,
    objwithtomany,
    objwithtomanycont,
    objwithtoone,
)
from Products.ZenRelations.tests.TestSchema import (  # noqa F403
    Device,
    IpInterface,
    Location,
)
from Products.ZenRelations.tests.ZenRelationsBaseTest import (  # noqa F403
    ZenRelationsBaseTest,
)


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
        "test exporting rm with to-one relationship"
        dev = self.build(self.app, Device, "dev")
        loc = self.build(self.app, Location, "loc")
        dev.location.addRelation(loc)
        ofile = StringIO.StringIO()
        dev.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtoone)

    def testExportToMany(self):
        "test exporting rm with to-many relationship"
        dev = self.build(self.app, Device, "dev")
        loc = self.build(self.app, Location, "loc")
        dev.location.addRelation(loc)
        ofile = StringIO.StringIO()
        loc.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtomany)

    def testExportToManyCont(self):
        "test exporting rm with properties"
        dev = self.build(self.app, Device, "dev")
        self.create(dev.interfaces, IpInterface, "eth0")
        ofile = StringIO.StringIO()
        dev.exportXml(ofile)
        self.assert_(ofile.getvalue() == objwithtomanycont)


class ImportTest(ZenRelationsBaseTest):
    """Import Tests"""

    def testImportObject(self):
        "test importing rm without properties"
        self.failIf(hasattr(self.app, "loc"))
        self.failIf(hasattr(self.app, "dev"))
        im = NoLoginImportRM(self.app)
        infile = StringIO.StringIO(objnoprops)
        im.loadObjectFromXML(infile)
        self.assert_(self.app.loc)
        self.assertEqual("loc", self.app.loc.id)
        self.assertEqual(
            "Products.ZenRelations.tests.TestSchema", self.app.loc.__module__
        )
        self.assertEqual("Location", self.app.loc.__class__.__name__)
        self.failIf(hasattr(self.app, "dev"))

    def testImportProperties(self):
        "test importing rm with properties"
        self.failIf(hasattr(self.app, "loc"))
        self.failIf(hasattr(self.app, "dev"))
        im = NoLoginImportRM(self.app)
        infile = StringIO.StringIO(objwithprops)
        im.loadObjectFromXML(infile)
        self.assert_(self.app.dev)
        self.assertEqual("dev", self.app.dev.id)
        self.assertEqual(
            "Products.ZenRelations.tests.TestSchema", self.app.dev.__module__
        )
        self.assertEqual("Device", self.app.dev.__class__.__name__)
        self.assertEqual(0, self.app.dev.pingStatus)
        self.failIf(hasattr(self.app, "loc"))

    def testImportToOne(self):
        "test importing rm with to-one relationship"
        self.failIf(hasattr(self.app, "dev"))
        self.build(self.app, Location, "loc")
        self.assert_(hasattr(self.app, "loc"))
        im = NoLoginImportRM(self.app)
        xml = "<objects>" + objwithtoone + "</objects>"
        im.loadObjectFromXML(StringIO.StringIO(xml))
        self.assert_(self.app.dev)
        self.assert_(self.app.loc)
        self.assert_(self.app.dev.location())
        self.assertEqual("loc", self.app.dev.location().id)
        self.assertEqual(1, len(self.app.loc.devices()))
        self.assert_("dev", self.app.loc.devices()[0].id)

    def testImportToManyCont(self):
        "test importing rm with properties"
        self.failIf(hasattr(self.app, "loc"))
        self.failIf(hasattr(self.app, "dev"))
        im = NoLoginImportRM(self.app)
        infile = StringIO.StringIO(objwithtomanycont)
        im.loadObjectFromXML(infile)
        self.assert_(self.app.dev)
        self.assertEqual(1, len(self.app.dev.interfaces()))
        self.assert_(self.app.dev.interfaces.eth0)
        self.assertEqual(
            "IpInterface", self.app.dev.interfaces.eth0.__class__.__name__
        )
        self.assertEqual("dev", self.app.dev.id)
        self.assertEqual(
            "Products.ZenRelations.tests.TestSchema", self.app.dev.__module__
        )
        self.assertEqual("Device", self.app.dev.__class__.__name__)
        self.assertEqual(0, self.app.dev.pingStatus)
        self.failIf(hasattr(self.app, "loc"))

    def testImportSkip(self):
        """test skipping vmware relations that are not relevant to the
        standard device class"""
        self.failIf(hasattr(self.dmd.Devices, "dev"))
        im = NoLoginImportRM(self.dmd.Devices)
        infile = StringIO.StringIO(objwithskip)
        im.loadObjectFromXML(infile)
        self.assert_(self.dmd.Devices.dev)
        self.failIf(hasattr(self.dmd.Devices.dev, "guestDevices"))


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(ExportTest))
    suite.addTest(makeSuite(ImportTest))
    return suite


if __name__ == "__main__":
    framework()  # noqa F405
    # unittest.main()
