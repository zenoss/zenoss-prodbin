##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
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
import unittest

from Acquisition import aq_base
from OFS.Cache import isCacheable

from Products.StandardCacheManagers.RAMCacheManager import RAMCacheManager

class FauxRequest:

    def __init__( self, steps=(), **kw ):

        self.steps = steps
        self._dict = {}
        self._dict.update( kw )

    def get( self, key, default=None ):

        return self._dict.get( key, default )

    def _authUserPW( self ):
        form = self.get( 'form' )
        return ( form.get( 'login' ), form.get( 'password' ) )

    def __getitem__( self, key ):

        return self._dict[ key ]

    def __setitem__( self, key, value ):

        self._dict[ key ] = value

class PluggableAuthServiceCachingTests( unittest.TestCase ):

    def tearDown( self ):
        pass


    def _getTargetClass( self ):

        from Products.PluggableAuthService.PluggableAuthService \
            import PluggableAuthService

        return PluggableAuthService

    def _makeOne( self, plugins=None, *args, **kw ):

        zcuf = self._getTargetClass()( *args, **kw )

        if plugins is not None:
            zcuf._setObject( 'plugins', plugins )

        rcm = RAMCacheManager('ramcache')
        zcuf._setObject('ramcache', rcm)

        return zcuf

    def _makePlugins( self, plugin_type_info=None ):

        from Products.PluggableAuthService.PluggableAuthService \
            import _PLUGIN_TYPE_INFO
        from Products.PluginRegistry.PluginRegistry import PluginRegistry

        if plugin_type_info is None:
            plugin_type_info = _PLUGIN_TYPE_INFO

        reg = PluginRegistry( plugin_type_info=plugin_type_info )
        reg._setId( 'plugins' )
        reg._plugins = {}

        return reg

    def _makeAndFill(self):

        from Products.PluggableAuthService.plugins import ZODBUserManager
        from Products.PluggableAuthService.plugins import ZODBRoleManager

        plugin_registry = self._makePlugins()
        user_source = ZODBUserManager.ZODBUserManager('zodb_users')
        roles_source = ZODBRoleManager.ZODBRoleManager('zodb_roles')
        pas_instance = self._makeOne(plugins=plugin_registry)
        pas_instance._setObject('zodb_users', user_source)
        pas_instance._setObject('zodb_roles', roles_source)

        return pas_instance

    def test_empty( self ):
        zcuf = self._makeOne()
        rcm = getattr(zcuf, 'ramcache')

        # This is needed because some underlying ZCacheable code wants to
        # use self.REQUEST :/
        setattr(rcm, 'REQUEST', FauxRequest())

        # Make sure the PAS instance itself is Cacheable
        self.assert_(isCacheable(zcuf))

        # Make sure the PAS instance is not associated with any cache manager
        # by default
        self.assert_(zcuf.ZCacheable_getManager() is None)

        # Make sure the RAMCacheManager is empty
        self.assert_(len(rcm.getCacheReport()) == 0)

    def test_caching_in_PAS(self):
        zcuf = self._makeAndFill()
        rcm = getattr(zcuf, 'ramcache')
        plugin_registry = getattr(zcuf, 'plugins')
        user_source = getattr(zcuf, 'zodb_users')
        roles_source = getattr(zcuf, 'zodb_roles')

        # This is needed because some underlying ZCacheable code wants to
        # use self.REQUEST :/
        setattr(zcuf, 'REQUEST', FauxRequest())

        # First, we register the ZODBUserManager as a plugin suitable
        # for storing and returning user objects and the ZODBRoleManager
        # for roles. Basic scaffolding to be able to store and retrieve users.
        from Products.PluggableAuthService.interfaces import plugins

        plugin_registry.activatePlugin( plugins.IUserEnumerationPlugin
                                      , user_source.getId()
                                      )
        plugin_registry.activatePlugin( plugins.IUserAdderPlugin
                                      , user_source.getId()
                                      )
        plugin_registry.activatePlugin( plugins.IRolesPlugin
                                      , roles_source.getId()
                                      )
        plugin_registry.activatePlugin( plugins.IRoleEnumerationPlugin
                                      , roles_source.getId()
                                      )
        plugin_registry.activatePlugin( plugins.IRoleAssignerPlugin
                                      , roles_source.getId()
                                      )

        # Now add a user and make sure it's there
        zcuf._doAddUser('testlogin', 'secret', ['Member', 'Anonymous'], [])
        self.failIf(zcuf.getUser('testlogin') is None)

        # Then we activate caching for the PAS instance itself
        zcuf.ZCacheable_setManagerId(rcm.getId())

        # Make sure the PAS instance is associated with the cache
        self.failUnless(aq_base(zcuf.ZCacheable_getManager()) is aq_base(rcm))

        # Now we can see if the cache is getting used. Test for emptiness
        # first, then retrieve a user, and the cache should have content.
        # Then test again to see if the cache entries are being used.
        # This is a bit nasty because I am relying on knowing the structure
        # of the cache report, which is really an internal implementation
        # detail.

        # First check: The cache must be empty
        report = rcm.getCacheReport()
        self.failUnless(len(report) == 0)

        # The user is being requested once. At this point there must be one
        # entry for the PAS instance. The number of "misses" must be >0 because
        # the first cache check will have failed. The number of cache hits must
        # be zero.
        zcuf.getUser('testlogin')
        report = rcm.getCacheReport()
        self.failUnless(len(report) == 1)
        report_item = report[0]
        firstpass_misses = report_item.get('misses')
        firstpass_hits = report_item.get('hits')
        firstpass_entries = report_item.get('entries')
        self.failUnless(firstpass_misses > 0)
        self.failUnless(firstpass_hits == 0)

        # The user is requested again. This request should produce a cache hit,
        # so the number of "misses" must have stayed the same as after the
        # first pass, but the number of hits must now be >0. Also, the number
        # of in-memory entries must have remained the same to prove that we are
        # reusing the same cache entries.
        zcuf.getUser('testlogin')
        report = rcm.getCacheReport()
        self.failUnless(len(report) == 1)
        report_item = report[0]
        self.failIf(report_item.get('misses') != firstpass_misses)
        self.failUnless(report_item.get('hits') > firstpass_hits)
        self.failIf(report_item.get('entries') != firstpass_entries)


if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( PluggableAuthServiceCachingTests ),
        ))
