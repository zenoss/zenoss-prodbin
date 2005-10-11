#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals

from ZenModelBaseTest import ZenModelBaseTest

from Products.ZenModel.Exceptions import *

from Products.ZenModel.Organizer import *

class OrganizerTest(ZenModelBaseTest):

    def testOrganizer(self):
        org = self.create(self.dmd, Organizer, "org")
        org.dmdRootName = "org"
        bar = org.createOrganizer("/foo/bar")
        foo = org._getOb("foo")
        self.assert_(foo in org.children())
        self.assert_("foo" in org.childIds())
        self.assert_(org.countChildren() == 2)
        self.assert_(org.unrestrictedTraverse("foo/bar") == bar)
        self.assert_(org.getOrganizer("/foo/bar") == bar)
        self.assert_(bar.getOrganizerName() == "/foo/bar")
        self.assert_(org.getOrganizerNames() == ["/foo", "/foo/bar"])


def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
