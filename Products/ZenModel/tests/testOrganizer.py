#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
  
from Products.ZenModel.Exceptions import *
from Products.ZenModel.Organizer import *

from ZenModelBaseTest import ZenModelBaseTest
  
class TestOrganizer(ZenModelBaseTest):
  
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

        self.assert_('/foo' in org.getOrganizerNames())
        self.assert_('/foo/bar' in org.getOrganizerNames())
        self.assert_('/foo' in org.deviceMoveTargets())
        self.assert_('/foo/bar' in org.deviceMoveTargets())
        self.assert_('/foo' in org.childMoveTargets())
        self.assert_('/foo/bar' in org.childMoveTargets())

        self.assert_(org.getDmdKey() == '/')
        self.assert_(foo in org.getSubOrganizers())
        self.assert_(bar in org.getSubOrganizers())

        self.assert_(org.getChildMoveTarget('/foo') == foo)
        self.assert_(org.getChildMoveTarget('/foo/bar') == bar)


    def testManageOrganizer(self):
        org = self.create(self.dmd,Organizer,'org')
        org.dmdRootName = "org"
        org.manage_addOrganizer('/foo/bar')
        org.manage_addOrganizer('/test/loc')
        org.manage_addOrganizer('/number/three')
        foo = org.getOrganizer('/foo')
        test = org.getOrganizer('/test')
        number = org.getOrganizer('/number')
        self.assert_(foo in org.children())
        self.assert_(test in org.children())
        self.assert_(number in org.children())
        org.manage_deleteOrganizer('/foo')
        self.assert_(foo not in org.children())
        org.manage_deleteOrganizers(['/test','/number'])
        self.assert_(org.children() == [])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestOrganizer))
    return suite

if __name__=="__main__":
    framework()
