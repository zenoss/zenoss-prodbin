##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import os, sys, base64, unittest

from Products.PluggableAuthService.tests import pastc

from AccessControl import Unauthorized
from AccessControl.Permissions import view as View
from AccessControl.Permissions import add_folders as AddFolders

from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService


class UserFolderTests(pastc.PASTestCase):

    def afterSetUp(self):
        # Set up roles and a user
        self.uf = self.folder.acl_users
        self.folder._addRole('role1')
        self.folder.manage_role('role1', [View])
        self.uf.roles.addRole('role1')
        self.folder._addRole('role2')
        self.folder.manage_role('role2', [View])
        self.uf.roles.addRole('role2')
        self.uf._doAddUser('user1', 'secret', ['role1'], [])
        # Set up a published object accessible to user
        self.folder.addDTMLMethod('doc', file='the document')
        self.doc = self.folder.doc
        self.doc.manage_permission(View, ['role1'], acquire=0)
        # Rig the REQUEST so it looks like we traversed to doc
        self.app.REQUEST['PUBLISHED'] = self.doc
        self.app.REQUEST['PARENTS'] = [self.app, self.folder]
        self.app.REQUEST.steps = list(self.doc.getPhysicalPath())
        self.basic = 'Basic %s' % base64.encodestring('user1:secret').rstrip()
        # Make sure we are not logged in
        self.logout()

    def testGetUser(self):
        self.failIfEqual(self.uf.getUser('user1'), None)

    def testGetBadUser(self):
        self.assertEqual(self.uf.getUser('user2'), None)

    def testGetUserById(self):
        self.failIfEqual(self.uf.getUserById('user1'), None)

    def testGetBadUserById(self):
        self.assertEqual(self.uf.getUserById('user2'), None)

    def NOTIMPLEMENTED_testGetUsers(self):
        users = self.uf.getUsers()
        self.failUnless(users)
        self.assertEqual(users[0].getUserName(), 'user1')

    def NOTIMPLEMENTED_testGetUserNames(self):
        names = self.uf.getUserNames()
        self.failUnless(names)
        self.assertEqual(names[0], 'user1')

    def NOTIMPLEMENTED_testIdentify(self):
        name, password = self.uf.identify(self.basic)
        self.assertEqual(name, 'user1')
        self.assertEqual(password, 'secret')

    def testGetRoles(self):
        user = self.uf.getUser('user1')
        self.failUnless('role1' in user.getRoles())
        self.failIf('role2' in user.getRoles())

    def testGetRolesInContext(self):
        user = self.uf.getUser('user1')
        self.folder.manage_addLocalRoles('user1', ['role2'])
        roles = user.getRolesInContext(self.folder)
        self.failUnless('role1' in roles)
        self.failUnless('role2' in roles)

    def testHasRole(self):
        user = self.uf.getUser('user1')
        self.failUnless(user.has_role('role1', self.folder))

    def testHasLocalRole(self):
        user = self.uf.getUser('user1')
        self.failIf(user.has_role('role2', self.folder))
        self.folder.manage_addLocalRoles('user1', ['role2'])
        self.failUnless(user.has_role('role2', self.folder))

    def testHasPermission(self):
        user = self.uf.getUser('user1')
        self.failUnless(user.has_permission(View, self.folder))
        self.failIf(user.has_permission(AddFolders, self.folder))
        self.folder.manage_role('role1', [AddFolders])
        self.failUnless(user.has_permission(AddFolders, self.folder))

    def testHasLocalRolePermission(self):
        user = self.uf.getUser('user1')
        self.folder.manage_role('role2', [AddFolders])
        self.failIf(user.has_permission(AddFolders, self.folder))
        self.folder.manage_addLocalRoles('user1', ['role2'])
        self.failUnless(user.has_permission(AddFolders, self.folder))

    def NOTIMPLEMENTED_testAuthenticate(self):
        user = self.uf.getUser('user1')
        self.failUnless(user.authenticate('secret', self.app.REQUEST))

    def testValidate(self):
        # XXX: PAS validate ignores auth argument
        self.app.REQUEST._auth = self.basic
        user = self.uf.validate(self.app.REQUEST, self.basic, ['role1'])
        self.failIfEqual(user, None)
        self.assertEqual(user.getUserName(), 'user1')

    def testNotValidateWithoutAuth(self):
        # XXX: PAS validate ignores auth argument
        user = self.uf.validate(self.app.REQUEST, '', ['role1'])
        self.assertEqual(user, None)

    def testValidateWithoutRoles(self):
        # Note - calling uf.validate without specifying roles will cause
        # the security machinery to determine the needed roles by looking
        # at the object itself (or its container). I'm putting this note
        # in to clarify because the original test expected failure but it
        # really should have expected success, since the user and the
        # object being checked both have the role 'role1', even though no
        # roles are passed explicitly to the userfolder validate method.
        # XXX: PAS validate ignores auth argument
        self.app.REQUEST._auth = self.basic
        user = self.uf.validate(self.app.REQUEST, self.basic)
        self.assertEqual(user.getUserName(), 'user1')

    def testNotValidateWithEmptyRoles(self):
        # XXX: PAS validate ignores auth argument
        self.app.REQUEST._auth = self.basic
        user = self.uf.validate(self.app.REQUEST, self.basic, [])
        self.assertEqual(user, None)

    def testNotValidateWithWrongRoles(self):
        # XXX: PAS validate ignores auth argument
        self.app.REQUEST._auth = self.basic
        user = self.uf.validate(self.app.REQUEST, self.basic, ['role2'])
        self.assertEqual(user, None)

    def testAllowAccessToUser(self):
        self.login('user1')
        try:
            self.folder.restrictedTraverse('doc')
        except Unauthorized:
            self.fail('Unauthorized')

    def testDenyAccessToAnonymous(self):
        self.assertRaises(Unauthorized, self.folder.restrictedTraverse, 'doc')

    def testMaxListUsers(self):
        # create a folder-ish thing which contains a roleManager,
        # then put an acl_users object into the folde-ish thing

        class Folderish(PluggableAuthService):
            def __init__(self, size, count):
                self.maxlistusers = size
                self.users = []
                self.acl_users = self
                self.__allow_groups__ = self
                for i in xrange(count):
                    self.users.append("Nobody")

            def getUsers(self):
                return self.users

            def user_names(self):
                return self.getUsers()


        tinyFolderOver = Folderish(15, 20)
        tinyFolderUnder = Folderish(15, 10)

        assert tinyFolderOver.maxlistusers == 15
        assert tinyFolderUnder.maxlistusers == 15
        assert len(tinyFolderOver.user_names()) == 20
        assert len(tinyFolderUnder.user_names()) == 10

        try:
            list = tinyFolderOver.get_valid_userids()
            assert 0, "Did not raise overflow error"
        except OverflowError:
            pass

        try:
            list = tinyFolderUnder.get_valid_userids()
            pass
        except OverflowError:
            assert 0, "Raised overflow error erroneously"

    def test__doAddUser_with_not_yet_encrypted_passwords(self):
        # See collector #1869 && #1926
        from AccessControl.AuthEncoding import is_encrypted

        USER_ID = 'not_yet_encrypted'
        PASSWORD = 'password'

        self.failIf(is_encrypted(PASSWORD))

        self.uf._doAddUser(USER_ID, PASSWORD, [], [])

        uid_and_info = self.uf.users.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))

    def test__doAddUser_with_preencrypted_passwords(self):
        # See collector #1869 && #1926
        from AccessControl.AuthEncoding import pw_encrypt

        USER_ID = 'already_encrypted'
        PASSWORD = 'password'

        ENCRYPTED = pw_encrypt(PASSWORD)

        self.uf._doAddUser(USER_ID, ENCRYPTED, [], [])

        uid_and_info = self.uf.users.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))


class UserTests(pastc.PASTestCase):

    def afterSetUp(self):
        self.uf = self.folder.acl_users
        self.uf._doAddUser('chris', '123', ['Manager'], [])
        self.user = self.uf.getUser('chris')

    def testGetUserName(self):
        f = self.user
        self.assertEqual(f.getUserName(), 'chris')

    def testGetUserId(self):
        f = self.user
        self.assertEqual(f.getId(), 'chris')

    def testBaseUserGetIdEqualGetName(self):
        # this is true for the default user type, but will not
        # always be true for extended user types going forward (post-2.6)
        f = self.user
        self.assertEqual(f.getId(), f.getUserName())

    def NOTIMPLEMENTED_testGetPassword(self):
        f = self.user
        self.assertEqual(f._getPassword(), '123')

    def testGetRoles(self):
        f = self.user
        # XXX: PAS returns roles as list
        #self.assertEqual(f.getRoles(), ('Manager', 'Authenticated'))
        self.assertEqual(f.getRoles(), ['Manager', 'Authenticated'])

    def testGetDomains(self):
        f = self.user
        self.assertEqual(f.getDomains(), ())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UserFolderTests))
    suite.addTest(unittest.makeSuite(UserTests))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
