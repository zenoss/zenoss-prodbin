##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Cookie crumbler xml adapter and setup handler unit tests.

$Id: test_cookieauth.py 39963 2005-11-07 19:06:45Z tseaver $
"""

import unittest
import Testing

import Products
from OFS.Folder import Folder
from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.CookieCrumbler import CookieCrumbler
from Products.CMFCore.tests.base.testcase import PlacelessSetup

_COOKIECRUMBLER_BODY = """\
<?xml version="1.0"?>
<object name="foo_cookiecrumbler" meta_type="Cookie Crumbler">
 <property name="auth_cookie">__ac</property>
 <property name="name_cookie">__ac_name</property>
 <property name="pw_cookie">__ac_password</property>
 <property name="persist_cookie">__ac_persistent</property>
 <property name="auto_login_page">login_form</property>
 <property name="logout_page">logged_out</property>
 <property name="unauth_page"></property>
 <property name="local_cookie_path">False</property>
 <property name="cache_header_value">private</property>
 <property name="log_username">True</property>
</object>
"""

_DEFAULT_EXPORT = """\
<?xml version="1.0"?>
<object name="foo_cookiecrumbler" meta_type="Cookie Crumbler">
 <property name="auth_cookie">__ac</property>
 <property name="name_cookie">__ac_name</property>
 <property name="pw_cookie">__ac_password</property>
 <property name="persist_cookie">__ac_persistent</property>
 <property name="auto_login_page">login_form</property>
 <property name="logout_page">logged_out</property>
 <property name="unauth_page"></property>
 <property name="local_cookie_path">False</property>
 <property name="cache_header_value">private</property>
 <property name="log_username">True</property>
</object>
"""

_CHANGED_EXPORT = """\
<?xml version="1.0"?>
<object name="foo_cookiecrumbler" meta_type="Cookie Crumbler">
 <property name="auth_cookie">value1</property>
 <property name="name_cookie">value3</property>
 <property name="pw_cookie">value5</property>
 <property name="persist_cookie">value4</property>
 <property name="auto_login_page">value6</property>
 <property name="logout_page">value8</property>
 <property name="unauth_page">value7</property>
 <property name="local_cookie_path">True</property>
 <property name="cache_header_value">value2</property>
 <property name="log_username">False</property>
</object>
"""


class CookieCrumblerXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.cookieauth \
                import CookieCrumblerXMLAdapter

        return CookieCrumblerXMLAdapter

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.CookieCrumbler import CookieCrumbler

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = CookieCrumbler('foo_cookiecrumbler')
        self._BODY = _COOKIECRUMBLER_BODY


class _CookieCrumblerSetup(PlacelessSetup, BaseRegistryTests):

    def _initSite(self, use_changed=False):
        self.root.site = Folder(id='site')
        site = self.root.site
        cc = site.cookie_authentication = CookieCrumbler('foo_cookiecrumbler')
 
        if use_changed:
            cc.auth_cookie = 'value1'
            cc.cache_header_value = 'value2'
            cc.name_cookie = 'value3'
            cc.log_username = 0
            cc.persist_cookie = 'value4'
            cc.pw_cookie = 'value5'
            cc.local_cookie_path = 1
            cc.auto_login_page = 'value6'
            cc.unauth_page = 'value7'
            cc.logout_page = 'value8'

        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportCookieCrumblerTests(_CookieCrumblerSetup):

    def test_unchanged(self):
        from Products.CMFCore.exportimport.cookieauth \
                import exportCookieCrumbler

        site = self._initSite(use_changed=False)
        context = DummyExportContext(site)
        exportCookieCrumbler(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'cookieauth.xml')
        self._compareDOM(text, _DEFAULT_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_changed(self):
        from Products.CMFCore.exportimport.cookieauth \
                import exportCookieCrumbler

        site = self._initSite(use_changed=True)
        context = DummyExportContext(site)
        exportCookieCrumbler(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'cookieauth.xml')
        self._compareDOM(text, _CHANGED_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importCookieCrumblerTests(_CookieCrumblerSetup):

    def test_normal(self):
        from Products.CMFCore.exportimport.cookieauth \
                import importCookieCrumbler

        site = self._initSite()
        cc = site.cookie_authentication

        context = DummyImportContext(site)
        context._files['cookieauth.xml'] = _CHANGED_EXPORT
        importCookieCrumbler(context)

        self.assertEqual( cc.auth_cookie, 'value1' )
        self.assertEqual( cc.cache_header_value, 'value2' )
        self.assertEqual( cc.name_cookie, 'value3' )
        self.assertEqual( cc.log_username, 0 )
        self.assertEqual( cc.persist_cookie, 'value4' )
        self.assertEqual( cc.pw_cookie, 'value5' )
        self.assertEqual( cc.local_cookie_path, 1 )
        self.assertEqual( cc.auto_login_page, 'value6' )
        self.assertEqual( cc.unauth_page, 'value7' )
        self.assertEqual( cc.logout_page, 'value8' )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(CookieCrumblerXMLAdapterTests),
        unittest.makeSuite(exportCookieCrumblerTests),
        unittest.makeSuite(importCookieCrumblerTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
