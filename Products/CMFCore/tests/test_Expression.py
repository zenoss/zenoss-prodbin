from unittest import TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from Products.CMFCore.ActionInformation import ActionInformation
from Products.CMFCore.Expression import createExprContext
from Products.CMFCore.Expression import Expression
from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummyTool as DummyMembershipTool
from Products.CMFCore.tests.base.testcase import SecurityTest


class ExpressionTests( SecurityTest ):

    def setUp( self ):

        SecurityTest.setUp(self)
        root = self.root
        root._setObject('portal', DummyContent('portal', url='url_portal'))
        portal = self.portal = root.portal
        self.folder = DummyContent('foo', url='url_foo')
        self.object = DummyContent('bar', url='url_bar')
        self.ai = ActionInformation(id='view'
                                  , title='View'
                                  , action=Expression(
                  text='view')
                                  , condition=Expression(
                  text='member')
                                  , category='global'
                                  , visible=1)

    def test_anonymous_ec(self):
        self.portal.portal_membership = DummyMembershipTool()
        ec = createExprContext(self.folder, self.portal, self.object)
        member = ec.global_vars['member']
        self.failIf(member)

    def test_authenticatedUser_ec(self):
        self.portal.portal_membership = DummyMembershipTool(anon=0)
        ec = createExprContext(self.folder, self.portal, self.object)
        member = ec.global_vars['member']
        self.assertEqual(member.getId(), 'dummy')

    def test_ec_context(self):
        self.portal.portal_membership = DummyMembershipTool()
        ec = createExprContext(self.folder, self.portal, self.object)
        object = ec.global_vars['object']
        portal = ec.global_vars['portal']
        folder = ec.global_vars['folder']
        self.failUnless(object)
        self.assertEqual(object.id, 'bar')
        self.assertEqual(object.absolute_url(), 'url_bar')
        self.failUnless(portal)
        self.assertEqual(portal.id, 'portal')
        self.assertEqual(portal.absolute_url(), 'url_portal')
        self.failUnless(folder)
        self.assertEqual(folder.id, 'foo')
        self.assertEqual(folder.absolute_url(), 'url_foo')


def test_suite():
    return TestSuite((
        makeSuite(ExpressionTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
