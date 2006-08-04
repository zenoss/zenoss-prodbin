##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit tests for MemberDataTool module.

$Id: test_MemberDataTool.py 38513 2005-09-19 12:01:33Z jens $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

import Acquisition

class DummyUserFolder(Acquisition.Implicit):

    def __init__(self):
        self._users = {}

    def _addUser(self, user):
        self._users[user.getUserName()] = user

    def userFolderEditUser(self, name, password, roles, domains):
        user = self._users[name]
        if password is not None:
            user.__ = password
        # Emulate AccessControl.User's stupid behavior (should test None)
        user.roles = tuple(roles)
        user.domains = tuple(domains)

    def getUsers(self):
        return self._users.values()


class DummyUser(Acquisition.Implicit):

    def __init__(self, name, password, roles, domains):
        self.name = name
        self.__ = password
        self.roles = tuple(roles)
        self.domains = tuple(domains)

    def getUserName(self):
        return self.name

    def getRoles(self):
        return self.roles + ('Authenticated',)

    def getDomains(self):
        return self.domains


class DummyMemberDataTool(Acquisition.Implicit):
    pass


class MemberDataToolTests(TestCase):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.MemberDataTool import MemberDataTool

        return MemberDataTool(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.portal_actions \
                import ActionProvider as IActionProvider
        from Products.CMFCore.interfaces.portal_memberdata \
                import portal_memberdata as IMemberDataTool
        from Products.CMFCore.MemberDataTool import MemberDataTool

        verifyClass(IActionProvider, MemberDataTool)
        verifyClass(IMemberDataTool, MemberDataTool)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IActionProvider
            from Products.CMFCore.interfaces import IMemberDataTool
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.MemberDataTool import MemberDataTool

        verifyClass(IActionProvider, MemberDataTool)
        verifyClass(IMemberDataTool, MemberDataTool)

    def test_deleteMemberData(self):
        tool = self._makeOne()
        tool.registerMemberData('Dummy', 'user_foo')
        self.failUnless( tool._members.has_key('user_foo') )
        self.failUnless( tool.deleteMemberData('user_foo') )
        self.failIf( tool._members.has_key('user_foo') )
        self.failIf( tool.deleteMemberData('user_foo') )

    def test_pruneMemberData(self):
        # This needs a tad more setup
        from OFS.Folder import Folder
        from Products.CMFCore.MembershipTool import MembershipTool
        folder = Folder('test')
        folder._setObject('portal_memberdata', self._makeOne())
        folder._setObject('portal_membership', MembershipTool())
        folder._setObject('acl_users', DummyUserFolder())
        tool = folder.portal_memberdata

        # Create some members
        for i in range(20):
            tool.registerMemberData( 'Dummy_%i' % i
                                   , 'user_foo_%i' % i
                                   )

        # None of these fake members are in the user folder, which means
        # there are 20 members and 20 "orphans"
        contents = tool.getMemberDataContents()
        info_dict = contents[0]
        self.assertEqual(info_dict['member_count'], 20)
        self.assertEqual(info_dict['orphan_count'], 20)

        # Calling the prune method should delete all orphans, so we end
        # up with no members in the tool.
        tool.pruneMemberDataContents()
        contents = tool.getMemberDataContents()
        info_dict = contents[0]
        self.assertEqual(info_dict['member_count'], 0)
        self.assertEqual(info_dict['orphan_count'], 0)


class MemberDataTests(TestCase):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.MemberDataTool import MemberData

        return MemberData(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.portal_memberdata \
                import MemberData as IMemberData
        from Products.CMFCore.MemberDataTool import MemberData

        verifyClass(IMemberData, MemberData)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IMemberData
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.MemberDataTool import MemberData

        verifyClass(IMemberData, MemberData)

    def test_setSecurityProfile(self):
        mdtool = DummyMemberDataTool()
        aclu = DummyUserFolder()
        user = DummyUser('bob', 'pw', ['Role'], ['domain'])
        aclu._addUser(user)
        user = user.__of__(aclu)
        member = self._makeOne(None, 'bob').__of__(mdtool).__of__(user)
        member.setSecurityProfile(password='newpw')
        self.assertEqual(user.__, 'newpw')
        self.assertEqual(list(user.roles), ['Role'])
        self.assertEqual(list(user.domains), ['domain'])
        member.setSecurityProfile(roles=['NewRole'])
        self.assertEqual(user.__, 'newpw')
        self.assertEqual(list(user.roles), ['NewRole'])
        self.assertEqual(list(user.domains), ['domain'])
        member.setSecurityProfile(domains=['newdomain'])
        self.assertEqual(user.__, 'newpw')
        self.assertEqual(list(user.roles), ['NewRole'])
        self.assertEqual(list(user.domains), ['newdomain'])


def test_suite():
    return TestSuite((
        makeSuite( MemberDataToolTests ),
        makeSuite( MemberDataTests ),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
