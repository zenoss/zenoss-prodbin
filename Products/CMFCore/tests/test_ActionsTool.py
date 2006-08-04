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
""" Unit tests for ActionsTool module.

$Id: test_ActionsTool.py 38418 2005-09-09 08:40:13Z yuppie $
"""

from unittest import TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from Products.CMFCore.MembershipTool import MembershipTool
from Products.CMFCore.RegistrationTool import RegistrationTool
from Products.CMFCore.tests.base.testcase import SecurityRequestTest
from Products.CMFCore.TypesTool import TypesTool
from Products.CMFCore.URLTool import URLTool


class ActionsToolTests( SecurityRequestTest ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ActionsTool import ActionsTool

        return ActionsTool(*args, **kw)

    def setUp(self):
        SecurityRequestTest.setUp(self)

        root = self.root
        root._setObject( 'portal_actions', self._makeOne() )
        root._setObject( 'portal_url', URLTool() )
        root._setObject( 'foo', URLTool() )
        root._setObject('portal_membership', MembershipTool())
        root._setObject('portal_types', TypesTool())
        self.tool = root.portal_actions
        self.tool.action_providers = ('portal_actions',)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ActionsTool import ActionsTool
        from Products.CMFCore.interfaces.portal_actions \
                import ActionProvider as IActionProvider
        from Products.CMFCore.interfaces.portal_actions \
                import portal_actions as IActionsTool

        verifyClass(IActionProvider, ActionsTool)
        verifyClass(IActionsTool, ActionsTool)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IActionProvider
            from Products.CMFCore.interfaces import IActionsTool
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ActionsTool import ActionsTool

        verifyClass(IActionProvider, ActionsTool)
        verifyClass(IActionsTool, ActionsTool)

    def test_actionProviders(self):
        tool = self.tool
        self.assertEqual(tool.listActionProviders(), ('portal_actions',))

    def test_addActionProvider(self):
        tool = self.tool
        tool.addActionProvider('foo')
        self.assertEqual(tool.listActionProviders(),
                          ('portal_actions', 'foo'))
        tool.addActionProvider('portal_url')
        tool.addActionProvider('foo')
        self.assertEqual(tool.listActionProviders(),
                          ('portal_actions', 'foo', 'portal_url'))

    def test_delActionProvider(self):
        tool = self.tool
        tool.deleteActionProvider('foo')
        self.assertEqual(tool.listActionProviders(),
                          ('portal_actions',))

    def test_listActionInformationActions(self):
        """
        Check that listFilteredActionsFor works for objects
        that return ActionInformation objects
        """
        root = self.root
        tool = self.tool
        root._setObject('portal_registration', RegistrationTool())
        self.tool.action_providers = ('portal_actions',)
        self.assertEqual(tool.listFilteredActionsFor(root.portal_registration),
                         {'workflow': [],
                          'user': [],
                          'object': [],
                          'folder': [{'permissions': ('List folder contents',),
                                      'id': 'folderContents',
                                      'url': 'http://foo/folder_contents',
                                      'title': 'Folder contents',
                                      'name': 'Folder contents',
                                      'visible': True,
                                      'available': True,
                                      'allowed': True,
                                      'category': 'folder'}],
                          'global': []})


def test_suite():
    return TestSuite((
        makeSuite(ActionsToolTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
