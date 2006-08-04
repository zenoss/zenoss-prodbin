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
""" Unit tests for DynamicType module.

$Id: test_DynamicType.py 38612 2005-09-25 13:02:39Z jens $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from Acquisition import Implicit
from ZPublisher.BaseRequest import BaseRequest
from ZPublisher.HTTPResponse import HTTPResponse

from Products.CMFCore.DynamicType import DynamicType
from Products.CMFCore.tests.base.dummy import DummyObject
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyTool
from Products.CMFCore.tests.base.testcase import SecurityRequestTest
from Products.CMFCore.tests.base.tidata import FTIDATA_CMF15
from Products.CMFCore.TypesTool import FactoryTypeInformation as FTI
from Products.CMFCore.TypesTool import TypesTool


class DummyContent(DynamicType, Implicit):
    """ Basic dynamic content class.
    """

    portal_type = 'Dummy Content 15'


class DynamicTypeTests(TestCase):

    def setUp(self):
        self.site = DummySite('site')
        self.site._setObject( 'portal_types', TypesTool() )
        fti = FTIDATA_CMF15[0].copy()
        self.site.portal_types._setObject( 'Dummy Content 15', FTI(**fti) )
        self.site._setObject( 'foo', DummyContent() )

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.Dynamic \
                import DynamicType as IDynamicType

        verifyClass(IDynamicType, DynamicType)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IDynamicType
        except ImportError:
            # BBB: for Zope 2.7
            return

        verifyClass(IDynamicType, DynamicType)

    def test___before_publishing_traverse__(self):
        dummy_view = self.site._setObject( 'dummy_view', DummyObject() )
        response = HTTPResponse()
        environment = { 'URL': '',
                        'PARENTS': [self.site],
                        'REQUEST_METHOD': 'GET',
                        'steps': [],
                        '_hacked_path': 0,
                        'response': response }
        r = BaseRequest(environment)

        r.traverse('foo')
        self.assertEqual( r.URL, '/foo/dummy_view' )
        self.assertEqual( r.response.base, '/foo/',
                          'CMF Collector issue #192 (wrong base): %s'
                          % (r.response.base or 'empty',) )


class DynamicTypeSecurityTests(SecurityRequestTest):

    def setUp(self):
        SecurityRequestTest.setUp(self)
        self.site = DummySite('site').__of__(self.root)
        self.site._setObject( 'portal_membership', DummyTool() )
        self.site._setObject( 'portal_types', TypesTool() )
        self.site._setObject( 'portal_url', DummyTool() )
        fti = FTIDATA_CMF15[0].copy()
        self.site.portal_types._setObject( 'Dummy Content 15', FTI(**fti) )
        self.site._setObject( 'foo', DummyContent() )

    def test_getTypeInfo(self):
        foo = self.site.foo
        self.assertEqual( foo.getTypeInfo().getId(), 'Dummy Content 15' )

    def test_getActionInfo(self):
        foo = self.site.foo
        self.assertEqual( foo.getActionInfo('object/view')['id'], 'view' )

        # The following is nasty, but I want to make sure the ValueError
        # carries some useful information
        INVALID_ID = 'invalid_id'
        try:
            rval = foo.getActionInfo('object/%s' % INVALID_ID)
        except ValueError, e:
            message = e.args[0]
            detail = '"%s" does not offer action "%s"' % (message, INVALID_ID)
            self.failUnless(message.find(INVALID_ID) != -1, detail)


def test_suite():
    return TestSuite((
        makeSuite(DynamicTypeTests),
        makeSuite(DynamicTypeSecurityTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
