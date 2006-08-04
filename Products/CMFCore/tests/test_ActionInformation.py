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
""" Unit tests for ActionInformation module.

$Id: test_ActionInformation.py 38418 2005-09-09 08:40:13Z yuppie $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from OFS.Folder import manage_addFolder
from Products.PythonScripts.PythonScript import manage_addPythonScript

from Products.CMFCore.Expression import createExprContext
from Products.CMFCore.Expression import Expression
from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyTool as DummyMembershipTool
from Products.CMFCore.tests.base.testcase import SecurityTest
from Products.CMFCore.tests.base.testcase import TransactionalTest


class ActionInfoTests(TestCase):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ActionInformation import ActionInfo

        return ActionInfo(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ActionInformation import ActionInfo
        from Products.CMFCore.interfaces.portal_actions \
                import ActionInfo as IActionInfo

        verifyClass(IActionInfo, ActionInfo)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IActionInfo
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ActionInformation import ActionInfo

        verifyClass(IActionInfo, ActionInfo)

    def test_create_from_ActionInformation(self):
        from Products.CMFCore.ActionInformation import ActionInformation

        wanted =  {'allowed': True, 'available': True, 'category': 'object',
                   'id': 'foo', 'name': 'foo', 'permissions': (),
                   'title': 'foo', 'url': '', 'visible': True}

        action = ActionInformation(id='foo')
        ec = None
        ai = self._makeOne(action, ec)

        self.assertEqual( ai['id'], wanted['id'] )
        self.assertEqual( ai['title'], wanted['title'] )
        self.assertEqual( ai['url'], wanted['url'] )
        self.assertEqual( ai['permissions'], wanted['permissions'] )
        self.assertEqual( ai['category'], wanted['category'] )
        self.assertEqual( ai['visible'], wanted['visible'] )
        self.assertEqual( ai['available'], wanted['available'] )
        self.assertEqual( ai['allowed'], wanted['allowed'] )
        self.assertEqual( ai, wanted )

    def test_create_from_dict(self):
        wanted =  {'allowed': True, 'available': True, 'category': 'object',
                   'id': 'foo', 'name': 'foo', 'permissions': (),
                   'title': 'foo', 'url': '', 'visible': True}

        action = {'name': 'foo', 'url': ''}
        ec = None
        ai = self._makeOne(action, ec)

        self.assertEqual( ai['id'], wanted['id'] )
        self.assertEqual( ai['title'], wanted['title'] )
        self.assertEqual( ai['url'], wanted['url'] )
        self.assertEqual( ai['permissions'], wanted['permissions'] )
        self.assertEqual( ai['category'], wanted['category'] )
        self.assertEqual( ai['visible'], wanted['visible'] )
        self.assertEqual( ai['available'], wanted['available'] )
        self.assertEqual( ai['allowed'], wanted['allowed'] )
        self.assertEqual( ai, wanted )


class ActionInfoSecurityTests(SecurityTest):

    def setUp(self):
        SecurityTest.setUp(self)
        self.site = DummySite('site').__of__(self.root)
        self.site._setObject( 'portal_membership', DummyMembershipTool() )

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ActionInformation import ActionInfo

        return ActionInfo(*args, **kw)

    def test_create_from_dict(self):
        WANTED = {'allowed': True, 'available': True, 'category': 'object',
                  'id': 'foo', 'name': 'foo', 'permissions': ('View',),
                  'title': 'foo', 'url': '', 'visible': True}

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.site, self.site, None)
        ai = self._makeOne(action, ec)

        self.assertEqual( ai['id'], WANTED['id'] )
        self.assertEqual( ai['title'], WANTED['title'] )
        self.assertEqual( ai['url'], WANTED['url'] )
        self.assertEqual( ai['category'], WANTED['category'] )
        self.assertEqual( ai['visible'], WANTED['visible'] )
        self.assertEqual( ai['available'], WANTED['available'] )
        self.assertEqual( ai['allowed'], WANTED['allowed'] )
        self.assertEqual( ai, WANTED )

    def test_category_object(self):
        # Permissions for action category 'object*' should be
        # evaluated in object context.
        manage_addFolder(self.site, 'actions_dummy')
        self.object = self.site.actions_dummy
        self.object.manage_permission('View', [], acquire=0)

        WANTED = {'allowed': False, 'category': 'object'}

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.site, self.site, self.object)
        ai = self._makeOne(action, ec)

        self.assertEqual( ai['category'], WANTED['category'] )
        self.assertEqual( ai['allowed'], WANTED['allowed'] )

    def test_category_folder(self):
        # Permissions for action category 'folder*' should be
        # evaluated in folder context.
        manage_addFolder(self.site, 'actions_dummy')
        self.folder = self.site.actions_dummy
        self.folder.manage_permission('View', [], acquire=0)

        WANTED = {'allowed': False, 'category': 'folder'}

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.folder, self.site, None)
        ai = self._makeOne(action, ec)
        ai['category'] = 'folder' # pfff

        self.assertEqual( ai['category'], WANTED['category'] )
        self.assertEqual( ai['allowed'], WANTED['allowed'] )

    def test_category_workflow(self):
        # Permissions for action category 'workflow*' should be
        # evaluated in object context.
        manage_addFolder(self.site, 'actions_dummy')
        self.object = self.site.actions_dummy
        self.object.manage_permission('View', [], acquire=0)

        WANTED = {'allowed': False, 'category': 'workflow'}

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.site, self.site, self.object)
        ai = self._makeOne(action, ec)
        ai['category'] = 'workflow' # pfff

        self.assertEqual( ai['category'], WANTED['category'] )
        self.assertEqual( ai['allowed'], WANTED['allowed'] )

    def test_category_document(self):
        # Permissions for action category 'document*' should be
        # evaluated in object context (not in portal context).
        manage_addFolder(self.site, 'actions_dummy')
        self.object = self.site.actions_dummy
        self.object.manage_permission('View', [], acquire=0)

        WANTED = {'allowed': False, 'category': 'document'}

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.site, self.site, self.object)
        ai = self._makeOne(action, ec)
        ai['category'] = 'document' # pfff

        self.assertEqual( ai['category'], WANTED['category'] )
        self.assertEqual( ai['allowed'], WANTED['allowed'] )

    def test_copy(self):

        action = {'name': 'foo', 'url': '', 'permissions': ('View',)}
        ec = createExprContext(self.site, self.site, None)
        ai = self._makeOne(action, ec)
        ai2 = ai.copy()

        self.assertEqual( ai._lazy_keys, ['allowed'] )
        self.assertEqual( ai2._lazy_keys, ['allowed'] )
        self.failIf( ai2._lazy_keys is ai._lazy_keys )
        self.assertEqual( ai['allowed'], True )
        self.assertEqual( ai2['allowed'], True )


class ActionInformationTests(TransactionalTest):

    def setUp( self ):

        TransactionalTest.setUp( self )

        root = self.root
        root._setObject('portal', DummyContent('portal', 'url_portal'))
        portal = self.portal = root.portal
        portal.portal_membership = DummyMembershipTool()
        self.folder = DummyContent('foo', 'url_foo')
        self.object = DummyContent('bar', 'url_bar')

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ActionInformation import ActionInformation

        return ActionInformation(*args, **kw)

    def test_basic_construction(self):
        ai = self._makeOne(id='view')

        self.assertEqual(ai.getId(), 'view')
        self.assertEqual(ai.Title(), 'view')
        self.assertEqual(ai.Description(), '')
        self.assertEqual(ai.getCondition(), '')
        self.assertEqual(ai.getActionExpression(), '')
        self.assertEqual(ai.getVisibility(), 1)
        self.assertEqual(ai.getCategory(), 'object')
        self.assertEqual(ai.getPermissions(), ())

    def test_editing(self):
        ai = self._makeOne(id='view', category='folder')
        ai.edit(id='new_id', title='blah')

        self.assertEqual(ai.getId(), 'new_id')
        self.assertEqual(ai.Title(), 'blah')
        self.assertEqual(ai.Description(), '')
        self.assertEqual(ai.getCondition(), '')
        self.assertEqual(ai.getActionExpression(), '')
        self.assertEqual(ai.getVisibility(), 1)
        self.assertEqual(ai.getCategory(), 'folder')
        self.assertEqual(ai.getPermissions(), ())

    def test_setActionExpression_with_string_prefix(self):
        from Products.CMFCore.Expression import Expression
        ai = self._makeOne(id='view', category='folder')
        ai.setActionExpression('string:blah')
        self.failUnless(isinstance(ai.action,Expression))
        self.assertEqual(ai.getActionExpression(), 'string:blah')

    def test_construction_with_Expressions(self):
        ai = self._makeOne( id='view',
                            title='View',
                            action=Expression(text='view'),
                            condition=Expression(text='member'),
                            category='global',
                            visible=False )

        self.assertEqual(ai.getId(), 'view')
        self.assertEqual(ai.Title(), 'View')
        self.assertEqual(ai.Description(), '')
        self.assertEqual(ai.getCondition(), 'member')
        self.assertEqual(ai.getActionExpression(), 'string:${object_url}/view')
        self.assertEqual(ai.getVisibility(), 0)
        self.assertEqual(ai.getCategory(), 'global')
        self.assertEqual(ai.getPermissions(), ())

    def test_Condition(self):
        portal = self.portal
        folder = self.folder
        object = self.object
        ai = self._makeOne( id='view',
                            title='View',
                            action=Expression(text='view'),
                            condition=Expression(text='member'),
                            category='global',
                            visible=True )
        ec = createExprContext(folder, portal, object)

        self.failIf(ai.testCondition(ec))

    def test_Condition_PathExpression(self):
        portal = self.portal
        folder = self.folder
        object = self.object
        manage_addPythonScript(self.root, 'test_script')
        script = self.root.test_script
        script.ZPythonScript_edit('', 'return context.getId()')
        ai = self._makeOne( id='view',
                            title='View',
                            action=Expression(text='view'),
                            condition=Expression(text='portal/test_script'),
                            category='global',
                            visible=True )
        ec = createExprContext(folder, portal, object)

        self.failUnless(ai.testCondition(ec))



def test_suite():
    return TestSuite((
        makeSuite(ActionInfoTests),
        makeSuite(ActionInfoSecurityTests),
        makeSuite(ActionInformationTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
