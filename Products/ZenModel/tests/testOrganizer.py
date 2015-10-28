##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import (
    DeviceExistsError, IpAddressConflict, IpCatalogNotFound, NoIPAddress,
    NoSnmp, PathNotFoundError, TraceRouteGap, WrongSubnetError, ZenModelError,
    ZentinelException)
from Products.ZenModel.Organizer import (
    ClassSecurityInfo, EventView, InitializeClass, MANAGER_ROLE,
    MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, Organizer, RELMETATYPES, RelSchema,
    TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, ToMany,
    ToManyCont, ToOne, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION,
    VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW,
    ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES,
    ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS,
    ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT,
    ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE,
    ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP,
    ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE,
    ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD,
    ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS,
    ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY,
    ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW,
    ZenModelRM, ZentinelException, aq_parent, audit, getDisplayName,
    getDisplayType, getSecurityManager, messaging)
from Products.Zuul import getFacade
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
        facade = getFacade('device', self.dmd)
        facade.deleteNode('/'.join(foo.getPhysicalPath()))
        self.assert_(foo not in org.children())
        getFacade('device', self.dmd).deleteNode('/'.join(test.getPhysicalPath()))
        getFacade('device', self.dmd).deleteNode('/'.join(number.getPhysicalPath()))
        self.assert_(org.children() == [])

    def testGetOrganizer(self):
        """
        Tests to make sure that getOrganizer uses acquisition. Sets up org/foo
        and org/quux organizers and asks for org/foo/quux.
        """
        org = self.create(self.dmd, Organizer, "org")
        org.dmdRootName = "org"
        foo = org.createOrganizer("/foo")
        quux = org.createOrganizer("/quux2")
        self.assertEqual(quux, org.getOrganizer("/foo/quux2"))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestOrganizer))
    return suite

if __name__=="__main__":
    framework()
