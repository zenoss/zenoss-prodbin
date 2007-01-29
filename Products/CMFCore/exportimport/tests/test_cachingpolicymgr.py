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
"""Caching policy manager xml adapter and setup handler unit tests.

$Id: test_cachingpolicymgr.py 40087 2005-11-13 19:55:09Z yuppie $
"""

import unittest
import Testing

import Products
from OFS.Folder import Folder
from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.testing import NodeAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.tests.base.testcase import PlacelessSetup

_CP_XML = """\
<caching-policy name="foo_policy" enable_304s="False" etag_func=""
   last_modified="True" max_age_secs="0" mtime_func="object/modified"
   must_revalidate="False" no_cache="False" no_store="False"
   no_transform="False" predicate="python:1" private="False"
   proxy_revalidate="False" public="False" vary=""/>
"""

_CPM_BODY = """\
<?xml version="1.0"?>
<object name="caching_policy_manager" meta_type="CMF Caching Policy Manager">
 <caching-policy name="foo_policy" enable_304s="False" etag_func=""
    last_modified="True" max_age_secs="600" mtime_func="object/modified"
    must_revalidate="False" no_cache="False" no_store="False"
    no_transform="False"
    predicate="python:object.getPortalTypeName() == 'Foo'" private="False"
    proxy_revalidate="False" public="False" vary=""/>
</object>
"""


class CachingPolicyNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.cachingpolicymgr \
                import CachingPolicyNodeAdapter

        return CachingPolicyNodeAdapter

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.CachingPolicyManager import CachingPolicy

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = CachingPolicy('foo_policy', max_age_secs=0)
        self._XML = _CP_XML


class CachingPolicyManagerXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.cachingpolicymgr \
                import CachingPolicyManagerXMLAdapter

        return CachingPolicyManagerXMLAdapter

    def _populate(self, obj):
        obj.addPolicy('foo_policy',
                      'python:object.getPortalTypeName() == \'Foo\'',
                      'object/modified', 600, 0, 0, 0, '', '')

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.CachingPolicyManager import CachingPolicyManager

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = CachingPolicyManager()
        self._BODY = _CPM_BODY


class _CachingPolicyManagerSetup(PlacelessSetup, BaseRegistryTests):

    POLICY_ID = 'policy_id'
    PREDICATE = "python:object.getId() == 'foo'"
    MTIME_FUNC = "object/modified"
    MAX_AGE_SECS = 60
    VARY = "Test"
    ETAG_FUNC = "object/getETag"
    S_MAX_AGE_SECS = 120
    PRE_CHECK = 42
    POST_CHECK = 43

    _EMPTY_EXPORT = """\
<?xml version="1.0"?>
<object name="caching_policy_manager" meta_type="CMF Caching Policy Manager"/>
"""

    _WITH_POLICY_EXPORT = """\
<?xml version="1.0"?>
<object name="caching_policy_manager" meta_type="CMF Caching Policy Manager">
 <caching-policy name="%s" enable_304s="True"
    etag_func="%s" last_modified="False" max_age_secs="%d"
    mtime_func="%s" must_revalidate="True" no_cache="True"
    no_store="True" no_transform="True" post_check="%d" pre_check="%d"
    predicate="%s" private="True"
    proxy_revalidate="True" public="True" s_max_age_secs="%d" vary="%s"/>
</object>
""" % (POLICY_ID, ETAG_FUNC, MAX_AGE_SECS, MTIME_FUNC, POST_CHECK, PRE_CHECK,
       PREDICATE, S_MAX_AGE_SECS, VARY)

    def _initSite(self, with_policy=False):
        from Products.CMFCore.CachingPolicyManager import CachingPolicyManager

        self.root.site = Folder(id='site')
        site = self.root.site
        mgr = CachingPolicyManager()
        site._setObject( mgr.getId(), mgr )

        if with_policy:
            mgr.addPolicy( policy_id=self.POLICY_ID
                         , predicate=self.PREDICATE
                         , mtime_func=self.MTIME_FUNC
                         , max_age_secs=self.MAX_AGE_SECS
                         , no_cache=True
                         , no_store=True
                         , must_revalidate=True
                         , vary=self.VARY
                         , etag_func=self.ETAG_FUNC
                         , s_max_age_secs=self.S_MAX_AGE_SECS
                         , proxy_revalidate=True
                         , public=True
                         , private=True
                         , no_transform=True
                         , enable_304s=True
                         , last_modified=False
                         , pre_check=self.PRE_CHECK
                         , post_check=self.POST_CHECK
                         )

        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportCachingPolicyManagerTests(_CachingPolicyManagerSetup):

    def test_empty(self):
        from Products.CMFCore.exportimport.cachingpolicymgr \
                import exportCachingPolicyManager

        site = self._initSite(with_policy=False)
        context = DummyExportContext(site)
        exportCachingPolicyManager(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'cachingpolicymgr.xml')
        self._compareDOM(text, self._EMPTY_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_with_policy(self):
        from Products.CMFCore.exportimport.cachingpolicymgr \
                import exportCachingPolicyManager

        site = self._initSite(with_policy=True)
        context = DummyExportContext(site)
        exportCachingPolicyManager(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'cachingpolicymgr.xml')
        self._compareDOM(text, self._WITH_POLICY_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importCachingPolicyManagerTests(_CachingPolicyManagerSetup):

    def test_normal(self):
        from Products.CMFCore.exportimport.cachingpolicymgr \
                import importCachingPolicyManager

        site = self._initSite(with_policy=False)
        cpm = site.caching_policy_manager
        self.assertEqual(len(cpm.listPolicies()), 0)

        context = DummyImportContext(site)
        context._files['cachingpolicymgr.xml'] = self._WITH_POLICY_EXPORT
        importCachingPolicyManager(context)

        self.assertEqual(len(cpm.listPolicies()), 1)
        policy_id, policy = cpm.listPolicies()[0]
        self.assertEqual(policy.getPolicyId(), self.POLICY_ID)
        self.assertEqual(policy.getPredicate(), self.PREDICATE)
        self.assertEqual(policy.getMTimeFunc(), self.MTIME_FUNC)
        self.assertEqual(policy.getVary(), self.VARY)
        self.assertEqual(policy.getETagFunc(), self.ETAG_FUNC)
        self.assertEqual(policy.getMaxAgeSecs(), self.MAX_AGE_SECS)
        self.assertEqual(policy.getSMaxAgeSecs(), self.S_MAX_AGE_SECS)
        self.assertEqual(policy.getPreCheck(), self.PRE_CHECK)
        self.assertEqual(policy.getPostCheck(), self.POST_CHECK)
        self.assertEqual(policy.getLastModified(), False)
        self.assertEqual(policy.getNoCache(), True)
        self.assertEqual(policy.getNoStore(), True)
        self.assertEqual(policy.getMustRevalidate(), True)
        self.assertEqual(policy.getProxyRevalidate(), True)
        self.assertEqual(policy.getNoTransform(), True)
        self.assertEqual(policy.getPublic(), True)
        self.assertEqual(policy.getPrivate(), True)
        self.assertEqual(policy.getEnable304s(), True)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(CachingPolicyNodeAdapterTests),
        unittest.makeSuite(CachingPolicyManagerXMLAdapterTests),
        unittest.makeSuite(exportCachingPolicyManagerTests),
        unittest.makeSuite(importCachingPolicyManagerTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
