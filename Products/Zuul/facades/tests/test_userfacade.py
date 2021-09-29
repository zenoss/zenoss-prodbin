##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import unittest
from zope.interface.verify import verifyClass
from Products.ZenModel.IpService import IpService
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.ZenModel.Service import Service
from Products.Zuul.interfaces import IComponent
from Products.PluggableAuthService import plugins

class UserFacadeTest(ZuulFacadeTestCase):

    def afterSetUp(self):
        super(UserFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('user', self.dmd)

        # verify that groupManager is enabled
        acl = self.facade._root.acl_users
        if not hasattr(acl, 'groupManager'):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, 'groupManager')
        acl.groupManager.manage_activateInterfaces(['IGroupsPlugin', ])

    def test_interfaces(self):
        verifyClass(IComponent, Service)

    def test_addUsers(self):
        u1 = self.facade.addUser("heman",  "MotU",  "heman@master.universe", ("ZenUser", "ZenManager", "Manager"))
        u2 = self.facade.addUser("shera",  "MotU",  "shera@master.universe", ("ZenUser",))
        u3 = self.facade.addUser("duncan", "MotU", "duncan@master.universe", ("ZenUser",))
        self.assertEqual(u1.id, 'heman')
        self.assertEqual(u2.id, 'shera')
        self.assertEqual(u3.id, 'duncan')
        users = self.facade._root.getAllUserSettingsNames()
        self.assertTrue('heman' in users)
        self.assertTrue('orco' not in users)

    def test_deleteUsers(self):
        if 'duncan' not in self.facade._root.getAllUserSettingsNames():
            # User needs to be in users list before removal
            u = self.facade.addUser("duncan", "MotU", "duncan@master.universe", ("ZenUser",))
            self.assertTrue('duncan' in self.facade._root.getAllUserSettingsNames())

        self.facade.removeUsers("duncan")
        self.assertTrue('duncan' not in self.facade._root.getAllUserSettingsNames())

    def test_createGroups(self):
        g1 = self.facade.createGroup("Universe Masters")
        g2 = self.facade.createGroup("Man at Arms")
        groups = self.facade._root.getAllGroupSettingsNames()
        self.assertTrue(g1.id in groups)
        self.assertTrue(g2.id in groups)

    def test_deleteGroups(self):
        groupName = "Man at Arms"
        if groupName not in self.facade._root.getAllGroupSettingsNames():
            # need to add the groups list before removal
            g = self.facade.createGroup(groupName)
            self.assertTrue(groupName, self.facade._root.getAllGroupSettingsNames())

        self.facade.removeGroups(groupName)
        self.assertTrue(groupName not in self.facade._root.getAllGroupSettingsNames())

    def test_assignAdminRoles(self):
        userName = 'shera'
        if userName not in self.facade._root.getAllUserSettingsNames():
            # User needs to be in users list before removal
            u = self.facade.addUser(userName, "MotU", "shera@master.universe", ("ZenUser",))
            self.assertTrue(userName in self.facade._root.getAllUserSettingsNames())

        # test assignment of admin
        roles = self.facade._root.getUser(userName).getRoles()
        self.assertTrue("Manager" not in roles)
        self.facade.assignAdminRolesToUsers(userName)
        roles = self.facade._root.getUser(userName).getRoles()
        self.assertTrue("Manager" in roles)

        # test removal of admin
        self.facade.removeAdminRolesFromUsers(userName)
        roles = self.facade._root.getUser(userName).getRoles()
        self.assertTrue("Manager" not in roles)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(UserFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
