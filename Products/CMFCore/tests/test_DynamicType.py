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

$Id: test_DynamicType.py 71509 2006-12-09 15:05:30Z philikon $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
import Zope2
Zope2.startup()

from StringIO import StringIO

from Acquisition import Implicit
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

from Products.CMFCore.DynamicType import DynamicType
from Products.CMFCore.tests.base.dummy import DummyObject
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyTool
from Products.CMFCore.tests.base.testcase import SecurityRequestTest
from Products.CMFCore.tests.base.tidata import FTIDATA_CMF15
from Products.CMFCore.TypesTool import FactoryTypeInformation as FTI
from Products.CMFCore.TypesTool import TypesTool

import zope.component
from zope.interface import Interface, implements
from zope.component.tests.placelesssetup import PlacelessSetup
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.app.publisher.interfaces.browser import IBrowserView

from Products.Five.traversable import FiveTraversable
from Products.Five.traversable import Traversable
from Products.Five.browser import BrowserView
from zope.app.traversing.adapters import Traverser
from zope.app.traversing.interfaces import ITraverser, ITraversable

def defineDefaultViewName(name, for_=None):
    try:
        from zope.component.interfaces import IDefaultViewName
        zope.component.provideAdapter(name, (for_, IBrowserRequest),
                                      IDefaultViewName, '')
    except ImportError:
        # BBB for Zope 2.8
        pres = zope.component.getService(zope.component.Presentation)
        pres.setDefaultViewName(for_, IBrowserRequest, name)

class IDummyContent(Interface):
    pass

class DummyContent(Traversable, DynamicType, Implicit):
    """ Basic dynamic content class.
    """
    implements(IDummyContent)
    portal_type = 'Dummy Content 15'


class DummyView(BrowserView):
    """This is a view"""


class DynamicTypeTests(TestCase):

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.Dynamic \
                import DynamicType as IDynamicType

        verifyClass(IDynamicType, DynamicType)

    def test_z3interfaces(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IDynamicType
        verifyClass(IDynamicType, DynamicType)

class DynamicTypeDefaultTraversalTests(PlacelessSetup, TestCase):

    def setUp(self):
        super(DynamicTypeDefaultTraversalTests, self).setUp()

        self.site = DummySite('site')
        self.site._setObject( 'portal_types', TypesTool() )
        fti = FTIDATA_CMF15[0].copy()
        self.site.portal_types._setObject( 'Dummy Content 15', FTI(**fti) )
        self.site._setObject( 'foo', DummyContent() )
        dummy_view = self.site._setObject( 'dummy_view', DummyObject() )

        try:
            from zope.component import provideAdapter
            provideAdapter(FiveTraversable, (None,), ITraversable)
            provideAdapter(Traverser, (None,), ITraverser)
        except ImportError:
            # BBB for Zope 2.8
            from zope.app.tests import ztapi
            ztapi.provideAdapter(None, ITraversable, FiveTraversable)
            ztapi.provideAdapter(None, ITraverser, Traverser)

    def test_default_view_from_fti(self):
        response = HTTPResponse()
        environment = { 'URL': '',
                        'PARENTS': [self.site],
                        'REQUEST_METHOD': 'GET',
                        'SERVER_NAME': 'localhost',
                        'SERVER_PORT': '80',
                        'REQUEST_METHOD': 'GET',
                        'steps': [],
                        '_hacked_path': 0}
        r = HTTPRequest(StringIO(), environment, response)
        r.other.update(environment)

        r.traverse('foo')
        self.assertEqual( r.URL, '/foo/dummy_view' )
        self.assertEqual( r.response.base, '/foo/',
                          'CMF Collector issue #192 (wrong base): %s'
                          % (r.response.base or 'empty',) )

    def test_default_viewname_but_no_view_doesnt_override_fti(self):
        response = HTTPResponse()
        environment = { 'URL': '',
                        'PARENTS': [self.site],
                        'REQUEST_METHOD': 'GET',
                        'SERVER_NAME': 'localhost',
                        'SERVER_PORT': '80',
                        'REQUEST_METHOD': 'GET',
                        'steps': [],
                        '_hacked_path': 0 }
        r = HTTPRequest(StringIO(), environment, response)
        r.other.update(environment)

        # we define a Zope3-style default view name, but no
        # corresponding view, no change in behaviour expected
        defineDefaultViewName('index.html', IDummyContent)
        r.traverse('foo')
        self.assertEqual( r.URL, '/foo/dummy_view' )
        self.assertEqual( r.response.base, '/foo/' )

    def test_default_viewname_overrides_fti(self):
        response = HTTPResponse()
        environment = { 'URL': '',
                        'PARENTS': [self.site],
                        'REQUEST_METHOD': 'GET',
                        'SERVER_PORT': '80',
                        'REQUEST_METHOD': 'GET',
                        'steps': [],
                        'SERVER_NAME': 'localhost',
                        '_hacked_path': 0 }
        r = HTTPRequest(StringIO(), environment, response)
        r.other.update(environment)

        # we define a Zope3-style default view name for which a view
        # actually exists
        defineDefaultViewName('index.html', IDummyContent)
        try:
            from zope.component import provideAdapter
            provideAdapter(DummyView, (DummyContent, IBrowserRequest),
                           IBrowserView, 'index.html')
        except ImportError:
            # BBB for Zope 2.8
            from zope.app.tests import ztapi
            ztapi.browserView(IDummyContent, 'index.html', DummyView)

        r.traverse('foo')
        self.assertEqual( r.URL, '/foo/index.html' )
        self.assertEqual( r.response.base, '/foo/' )


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
        makeSuite(DynamicTypeDefaultTraversalTests),
        makeSuite(DynamicTypeSecurityTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
