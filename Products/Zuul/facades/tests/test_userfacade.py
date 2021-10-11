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
        u1 = self.facade.addUser("Blitz", "Seahawks!", "blitz@seahawks.loc", ("Mascots",), ("ZenUser", "ZenManager", "Manager"))
        u2 = self.facade.addUser("Swoop", "Seahawks!", "swoop@seahawks.loc", ("Mascots",), ("ZenUser",))
        u3 = self.facade.addUser("Boom",  "Seahawks!",  "bool@seahawks.loc", ("Mascots",), ("ZenUser",))
        self.assertEqual(u1.id, 'Blitz')
        self.assertEqual(u2.id, 'Swoop')
        self.assertEqual(u3.id, 'Boom')
        users = self.facade._root.getAllUserSettingsNames()
        self.assertTrue('Blitz' in users)
        self.assertTrue('Taima' not in users)

    def test_deleteUsers(self):
        if 'Taima' not in self.facade._root.getAllUserSettingsNames():
            # User needs to be in users list before removal
            u = self.facade.addUser("Taima", "SeaHawks!", "taima@seahawks.loc", ("Animal",), ("ZenUser",))
            self.assertTrue('Taima' in self.facade._root.getAllUserSettingsNames())

        self.facade.removeUsers("Taima")
        self.assertTrue('Taima' not in self.facade._root.getAllUserSettingsNames())

    def test_createGroups(self):
        g1 = self.facade.createGroups(["Mascots"])
        g2 = self.facade.createGroups(["Animals"])
        groups = self.facade._root.getAllGroupSettingsNames()
        for g in g1:
            self.assertTrue(g.id in groups)
        for g in g2:
            self.assertTrue(g.id in groups)

    def test_deleteGroups(self):
        groupName = "Animals"
        if groupName not in self.facade._root.getAllGroupSettingsNames():
            # need to add the groups list before removal
            g = self.facade.createGroups([groupName])
            self.assertTrue(groupName, self.facade._root.getAllGroupSettingsNames())

        self.facade.removeGroups([groupName])
        self.assertTrue(groupName not in self.facade._root.getAllGroupSettingsNames())

    def test_assignAdminRoles(self):
        userName = 'Taima'
        if userName not in self.facade._root.getAllUserSettingsNames():
            # User needs to be in users list before removal
            u = self.facade.addUser(userName, "Seahawks!", "taima@seahawks.loc", ("Animals",), ("ZenUser",))
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
