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
""" Unit tests for PortalContent module.

$Id: test_PortalContent.py 69189 2006-07-18 18:48:28Z tseaver $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError:
    # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Acquisition import aq_base
try:
    import transaction
except ImportError:
    # BBB: for Zope 2.7
    from Products.CMFCore.utils import transaction

from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyUserFolder
from Products.CMFCore.tests.base.testcase import SecurityRequestTest
from Products.CMFCore.tests.base.dummy import DummyTool
from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummyObject
from OFS.Folder import Folder

class PortalContentTests(TestCase):

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.Contentish \
                import Contentish as IContentish
        from Products.CMFCore.interfaces.Dynamic \
                import DynamicType as IDynamicType
        from Products.CMFCore.PortalContent import PortalContent

        verifyClass(IContentish, PortalContent)
        verifyClass(IDynamicType, PortalContent)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IContentish
            from Products.CMFCore.interfaces import IDynamicType
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.PortalContent import PortalContent

        verifyClass(IContentish, PortalContent)
        verifyClass(IDynamicType, PortalContent)

    def _setupCallTests(self, aliases):
        # root
        root = Folder( 'root' )

        # set up dummy type info with problematic double-default alias
        root._setObject( 'portal_types', DummyTool() )
        root.portal_types.view_actions = aliases

        # dummy content and skin
        root._setObject( 'dummycontent', DummyContent() )
        root._setObject( 'dummy_view', DummyObject() )
        return root.dummycontent

    def test_DoubleDefaultAlias(self):
        test_aliases = ( ('(Default)', '(Default)'),
                         ('view', 'dummy_view'),
                       )
        ob = self._setupCallTests(test_aliases)
        # in unfixed version fail here with AttributeError
        # can end up with this arrangement using _getAliases though
        # in fixed version, falls through to _getViewFor, which is BBB
        self.assertEqual( ob(), 'dummy' )

    def test_BlankDefaultAlias(self):
        test_aliases = ( ('(Default)', ''),
                         ('view', 'dummy_view'),
                       )
        ob = self._setupCallTests(test_aliases)
        # blank default is BBB
        self.assertEqual( ob(), 'dummy' )

    def test_SpecificAlias(self):
        test_aliases = ( ('(Default)', 'dummy_view'),
                       )
        ob = self._setupCallTests(test_aliases)
        self.assertEqual( ob(), 'dummy' )

class TestContentCopyPaste(SecurityRequestTest):

    # Tests related to http://www.zope.org/Collectors/CMF/205
    # Copy/pasting a content item must set ownership to pasting user

    def setUp(self):
        SecurityRequestTest.setUp(self)

        self.root._setObject('site', DummySite('site'))
        self.site = self.root.site
        self.acl_users = self.site._setObject('acl_users', DummyUserFolder())

    def _initContent(self, folder, id):
        from Products.CMFCore.PortalContent import PortalContent

        c = PortalContent()
        c._setId(id)
        c.meta_type = 'File'
        folder._setObject(id, c)
        return folder._getOb(id)

    def test_CopyPasteSetsOwnership(self):
        # Copy/pasting a File should set new ownership including local roles
        from OFS.Folder import Folder

        acl_users = self.acl_users
        folder1 = self.site._setObject('folder1', Folder('folder1'))
        folder2 = self.site._setObject('folder2', Folder('folder2'))

        newSecurityManager(None, acl_users.user_foo)
        content = self._initContent(folder1, 'content')
        content.manage_setLocalRoles(acl_users.user_foo.getId(), ['Owner'])

        newSecurityManager(None, acl_users.all_powerful_Oz)
        cb = folder1.manage_copyObjects(['content'])
        folder2.manage_pasteObjects(cb)

        # Now test executable ownership and "owner" local role
        # "member" should have both.
        moved = folder2._getOb('content')
        self.assertEqual(aq_base(moved.getOwner()),
                         aq_base(acl_users.all_powerful_Oz))

        local_roles = moved.get_local_roles()
        self.assertEqual(len(local_roles), 1)
        userid, roles = local_roles[0]
        self.assertEqual(userid, acl_users.all_powerful_Oz.getId())
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0], 'Owner')


def test_suite():
    return TestSuite((
        makeSuite(PortalContentTests),
        makeSuite(TestContentCopyPaste),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
