##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights
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
""" Unit tests for plugin.exportimport

$Id: test_exportimport.py 40167 2005-11-16 18:50:53Z tseaver $
"""

import unittest

try:
    import Products.GenericSetup
except ImportError:  # No GenericSetup, so no tests

    print 'XXXX:  No GenericSetup!'
    def test_suite():
        return unittest.TestSuite()

else:

    from Products.GenericSetup.tests.conformance \
            import ConformsToIFilesystemExporter
    from Products.GenericSetup.tests.conformance \
            import ConformsToIFilesystemImporter

    from Products.GenericSetup.tests.common import SecurityRequestTest
    from Products.GenericSetup.tests.common import DOMComparator
    from Products.GenericSetup.tests.common import DummyExportContext
    from Products.GenericSetup.tests.common import DummyImportContext

    class _TestBase(SecurityRequestTest,
                    DOMComparator,
                    ConformsToIFilesystemExporter,
                    ConformsToIFilesystemImporter,
                    ):

        def _makeOne(self, context, *args, **kw):
            return self._getTargetClass()(context, *args, **kw)

    class ZODBUserManagerExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import ZODBUserManagerExportImport
            return ZODBUserManagerExportImport

        def _makePlugin(self, id='zodbusers', *args, **kw):
            from Products.PluggableAuthService.plugins.ZODBUserManager \
                import ZODBUserManager
            return ZODBUserManager(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)
            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.addUser('foo', 'bar', 'baz')
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(len(info['users']), 0)

        def test_export_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/empty.xml' )
            self._compareDOM( text, _EMPTY_ZODB_USERS )
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_with_users(self):

            plugin = self._makePlugin('with_users').__of__(self.root)
            plugin.title = 'Plugin Title'
            source_info = []

            for info in _ZODB_USER_INFO:
                info = info.copy()
                plugin.addUser(**info)
                hash = plugin._user_passwords[info['user_id']]
                info['password_hash'] = hash
                source_info.append(info)

            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], 'Plugin Title')
            self.assertEqual(len(info['users']), len(source_info))

            for x, y in zip(info['users'], source_info):
                self.assertEqual(x['user_id'], y['user_id'])
                self.assertEqual(x['login_name'], y['login_name'])
                self.assertEqual(x['password_hash'], y['password_hash'])

        def test_export_with_users(self):

            plugin = self._makePlugin('with_users').__of__(self.root)
            plugin.title = 'Plugin Title'

            hashes = []
            for info in _ZODB_USER_INFO:
                plugin.addUser(**info)
                hash = plugin._user_passwords[info['user_id']]
                hashes.append(hash)

            adapter = self._makeOne(plugin)
            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len(context._wrote), 1)
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual(filename, 'plugins/with_users.xml')
            self._compareDOM(text, _FILLED_ZODB_USERS % tuple(hashes))
            self.assertEqual(content_type, 'text/xml')

        def test_import_empty(self):
            HASHES = ('abcde', 'wxyz')
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/empty.xml'] = _FILLED_ZODB_USERS % HASHES
            self.assertEqual(plugin.title, None)

            adapter.import_(context, 'plugins', False)

            self.assertEqual(len(plugin._user_passwords), len(_ZODB_USER_INFO))
            self.assertEqual(plugin.title, 'Plugin Title')

            for info, hash in zip(_ZODB_USER_INFO, HASHES):
                user_id = info['user_id']
                self.assertEqual(plugin.getLoginForUserId(user_id),
                                info['login_name'])
                self.assertEqual(plugin._user_passwords[user_id], hash)

        def test_import_without_purge_leaves_existing_users(self):

            plugin = self._makePlugin('with_users').__of__(self.root)
            plugin.title = 'Plugin Title'

            for info in _ZODB_USER_INFO:
                plugin.addUser(**info)

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=False)
            context._files['plugins/with_users.xml'] = _EMPTY_ZODB_USERS

            self.assertEqual(len(plugin._user_passwords), len(_ZODB_USER_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._user_passwords), len(_ZODB_USER_INFO))
            self.assertEqual(plugin.title, None)

        def test_import_with_purge_wipes_existing_users(self):

            plugin = self._makePlugin('with_users').__of__(self.root)
            plugin.title = 'Plugin Title'

            for info in _ZODB_USER_INFO:
                plugin.addUser(**info)

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=True)
            context._files['plugins/with_users.xml'] = _EMPTY_ZODB_USERS

            self.assertEqual(len(plugin._user_passwords), len(_ZODB_USER_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._user_passwords), 0)
            self.assertEqual(plugin.title, None)

    class ZODBGroupManagerExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import ZODBGroupManagerExportImport
            return ZODBGroupManagerExportImport

        def _makePlugin(self, id, *args, **kw):
            from Products.PluggableAuthService.plugins.ZODBGroupManager \
                import ZODBGroupManager
            return ZODBGroupManager(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)
            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.addGroup('group_id', 'title', 'description')
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(len(info['groups']), 0)

        def test_export_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/empty.xml' )
            self._compareDOM( text, _EMPTY_ZODB_GROUPS )
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_with_groups(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _ZODB_GROUP_INFO:
                plugin.addGroup(g['group_id'], g['title'], g['description'])
                for principal in g['principals']:
                    plugin.addPrincipalToGroup(principal, g['group_id'])

            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], 'Plugin Title')
            self.assertEqual(len(info['groups']), len(_ZODB_GROUP_INFO))

            for x, y in zip(info['groups'], _ZODB_GROUP_INFO):
                self.assertEqual(x, y)

        def test_export_with_groups(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _ZODB_GROUP_INFO:
                plugin.addGroup(g['group_id'], g['title'], g['description'])
                for principal in g['principals']:
                    plugin.addPrincipalToGroup(principal, g['group_id'])

            adapter = self._makeOne(plugin)
            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len(context._wrote), 1)
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual(filename, 'plugins/with_groups.xml')
            self._compareDOM(text, _FILLED_ZODB_GROUPS)
            self.assertEqual(content_type, 'text/xml')

        def test_import_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/empty.xml'] = _FILLED_ZODB_GROUPS
            self.assertEqual(plugin.title, None)

            adapter.import_(context, 'plugins', False)

            found = plugin.listGroupInfo()
            self.assertEqual(len(found), len(_ZODB_GROUP_INFO))
            self.assertEqual(plugin.title, 'Plugin Title')

            for finfo, ginfo in zip(found, _ZODB_GROUP_INFO):
                self.assertEqual(finfo['id'], ginfo['group_id'])
                self.assertEqual(finfo['title'], ginfo['title'])
                self.assertEqual(finfo['description'], ginfo['description'])
                for principal_id in ginfo['principals']:
                    groups = plugin._principal_groups[principal_id]
                    self.failUnless(ginfo['group_id'] in groups)

        def test_import_without_purge_leaves_existing_users(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _ZODB_GROUP_INFO:
                plugin.addGroup(g['group_id'], g['title'], g['description'])
                for principal in g['principals']:
                    plugin.addPrincipalToGroup(principal, g['group_id'])

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=False)
            context._files['plugins/with_groups.xml'] = _EMPTY_ZODB_GROUPS

            self.assertEqual(len(plugin._groups), len(_ZODB_GROUP_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._groups), len(_ZODB_GROUP_INFO))
            self.assertEqual(plugin.title, None)

        def test_import_with_purge_wipes_existing_users(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _ZODB_GROUP_INFO:
                plugin.addGroup(g['group_id'], g['title'], g['description'])
                for principal in g['principals']:
                    plugin.addPrincipalToGroup(principal, g['group_id'])

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=True)
            context._files['plugins/with_groups.xml'] = _EMPTY_ZODB_GROUPS

            self.assertEqual(len(plugin._groups), len(_ZODB_GROUP_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._groups), 0)
            self.assertEqual(plugin.title, None)

    class ZODBRoleManagerExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import ZODBRoleManagerExportImport
            return ZODBRoleManagerExportImport

        def _makePlugin(self, id, *args, **kw):
            from Products.PluggableAuthService.plugins.ZODBRoleManager \
                import ZODBRoleManager
            return ZODBRoleManager(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.addRole('role_id', 'title', 'description')
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(len(info['roles']), 0)

        def test_export_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/empty.xml' )
            self._compareDOM( text, _EMPTY_ZODB_ROLES )
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_with_roles(self):

            plugin = self._makePlugin('with_roles').__of__(self.root)
            plugin.title = 'Plugin Title'

            for r in _ZODB_ROLE_INFO:
                plugin.addRole(r['role_id'], r['title'], r['description'])
                for principal in r['principals']:
                    plugin.assignRoleToPrincipal(r['role_id'], principal)

            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], 'Plugin Title')
            self.assertEqual(len(info['roles']), len(_ZODB_ROLE_INFO))

            for x, y in zip(info['roles'], _ZODB_ROLE_INFO):
                self.assertEqual(x, y)

        def test_export_with_roles(self):

            plugin = self._makePlugin('with_roles').__of__(self.root)
            plugin.title = 'Plugin Title'

            for r in _ZODB_ROLE_INFO:
                plugin.addRole(r['role_id'], r['title'], r['description'])
                for principal in r['principals']:
                    plugin.assignRoleToPrincipal(r['role_id'], principal)

            adapter = self._makeOne(plugin)
            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len(context._wrote), 1)
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual(filename, 'plugins/with_roles.xml')
            self._compareDOM(text, _FILLED_ZODB_ROLES)
            self.assertEqual(content_type, 'text/xml')

        def test_import_empty(self):
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/empty.xml'] = _FILLED_ZODB_ROLES
            self.assertEqual(plugin.title, None)

            adapter.import_(context, 'plugins', False)

            found = plugin.listRoleInfo()
            self.assertEqual(len(found), len(_ZODB_ROLE_INFO))
            self.assertEqual(plugin.title, 'Plugin Title')

            for finfo, rinfo in zip(found, _ZODB_ROLE_INFO):
                self.assertEqual(finfo['id'], rinfo['role_id'])
                self.assertEqual(finfo['title'], rinfo['title'])
                self.assertEqual(finfo['description'], rinfo['description'])
                for principal_id in rinfo['principals']:
                    roles = plugin._principal_roles[principal_id]
                    self.failUnless(rinfo['role_id'] in roles)

        def test_import_without_purge_leaves_existing_users(self):

            plugin = self._makePlugin('with_roles').__of__(self.root)
            plugin.title = 'Plugin Title'

            for r in _ZODB_ROLE_INFO:
                plugin.addRole(r['role_id'], r['title'], r['description'])
                for principal in r['principals']:
                    plugin.assignRoleToPrincipal(r['role_id'], principal)

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=False)
            context._files['plugins/with_roles.xml'] = _EMPTY_ZODB_ROLES

            self.assertEqual(len(plugin._roles), len(_ZODB_ROLE_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._roles), len(_ZODB_ROLE_INFO))
            self.assertEqual(plugin.title, None)

        def test_import_with_purge_wipes_existing_users(self):

            plugin = self._makePlugin('with_roles').__of__(self.root)
            plugin.title = 'Plugin Title'

            for r in _ZODB_ROLE_INFO:
                plugin.addRole(r['role_id'], r['title'], r['description'])
                for principal in r['principals']:
                    plugin.assignRoleToPrincipal(r['role_id'], principal)

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=True)
            context._files['plugins/with_roles.xml'] = _EMPTY_ZODB_ROLES

            self.assertEqual(len(plugin._roles), len(_ZODB_ROLE_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._roles), 0)
            self.assertEqual(plugin.title, None)

    class CookieAuthHelperExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import CookieAuthHelperExportImport
            return CookieAuthHelperExportImport

        def _makePlugin(self, id, *args, **kw):
            from Products.PluggableAuthService.plugins.CookieAuthHelper \
                import CookieAuthHelper
            return CookieAuthHelper(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.cookie_name = 'COOKIE_NAME'
            plugin.login_path = 'LOGIN_PATH'
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_default(self):
            from Products.PluggableAuthService.plugins.CookieAuthHelper \
                import CookieAuthHelper
            plugin = self._makePlugin('default').__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(info['cookie_name'], CookieAuthHelper.cookie_name)
            self.assertEqual(info['login_path'], CookieAuthHelper.login_path)

        def test_export_default(self):
            from Products.PluggableAuthService.plugins.CookieAuthHelper \
                import CookieAuthHelper as CAH
            plugin = self._makePlugin('default').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual(len(context._wrote), 1)
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'plugins/default.xml' )
            self._compareDOM(text,
                             _COOKIE_AUTH_TEMPLATE_NO_TITLE % (CAH.cookie_name,
                                                               CAH.login_path,
                                                              ))
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_explicitly_set(self):
            TITLE = 'Plugin Title'
            COOKIE_NAME = 'COOKIE_NAME'
            LOGIN_PATH = 'LOGIN_PATH'
            plugin = self._makePlugin('explicit').__of__(self.root)
            plugin.title = TITLE
            plugin.cookie_name = COOKIE_NAME
            plugin.login_path = LOGIN_PATH
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], TITLE)
            self.assertEqual(info['cookie_name'], COOKIE_NAME)
            self.assertEqual(info['login_path'], LOGIN_PATH)

        def test_export_explicitly_set(self):
            TITLE = 'Plugin Title'
            COOKIE_NAME = 'COOKIE_NAME'
            LOGIN_PATH = 'LOGIN_PATH'
            plugin = self._makePlugin('explicit').__of__(self.root)
            plugin.title = TITLE
            plugin.cookie_name = COOKIE_NAME
            plugin.login_path = LOGIN_PATH
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual(len(context._wrote), 1)
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'plugins/explicit.xml' )
            self._compareDOM(text,
                             _COOKIE_AUTH_TEMPLATE % (TITLE,
                                                      COOKIE_NAME,
                                                      LOGIN_PATH,
                                                     ))
            self.assertEqual( content_type, 'text/xml' )

        def test_import_with_title(self):
            TITLE = 'Plugin Title'
            COOKIE_NAME = 'COOKIE_NAME'
            LOGIN_PATH = 'LOGIN_PATH'
            plugin = self._makePlugin('with_title').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/with_title.xml'
                          ] = _COOKIE_AUTH_TEMPLATE % (TITLE,
                                                       COOKIE_NAME,
                                                       LOGIN_PATH,
                                                      )
            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, TITLE )
            self.assertEqual( plugin.cookie_name, COOKIE_NAME )
            self.assertEqual( plugin.login_path, LOGIN_PATH )

        def test_import_no_title(self):
            TITLE = 'Plugin Title'
            COOKIE_NAME = 'COOKIE_NAME'
            LOGIN_PATH = 'LOGIN_PATH'
            plugin = self._makePlugin('no_title').__of__(self.root)
            plugin.title = TITLE
            plugin.cookie_name = COOKIE_NAME
            plugin.login_path = LOGIN_PATH
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/no_title.xml'
                          ] = _COOKIE_AUTH_TEMPLATE_NO_TITLE % (COOKIE_NAME,
                                                                LOGIN_PATH,
                                                               )
            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, None )
            self.assertEqual( plugin.cookie_name, COOKIE_NAME )
            self.assertEqual( plugin.login_path, LOGIN_PATH )

    class DomainAuthHelperExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import DomainAuthHelperExportImport
            return DomainAuthHelperExportImport

        def _makePlugin(self, id, *args, **kw):
            from Products.PluggableAuthService.plugins.DomainAuthHelper \
                import DomainAuthHelper
            return DomainAuthHelper(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.cookie_name = 'COOKIE_NAME'
            plugin.login_path = 'LOGIN_PATH'
            plugin.manage_addMapping(user_id='user_id',
                                     match_type='equals',
                                     match_string='host.example.com',
                                     roles=['foo', 'bar'],
                                    )
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_empty(self):
            plugin = self._makePlugin('empty', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(len(info['map']), 0)

        def test_export_empty(self):
            plugin = self._makePlugin('empty', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/empty.xml' )
            self._compareDOM( text, _EMPTY_DOMAIN_AUTH )
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_with_map(self):
            TITLE = 'With Map'
            USER_ID = 'some_user_id'
            DOMAIN = 'host.example.com'
            ROLES = ['foo', 'bar']
            plugin = self._makePlugin('with_map', TITLE).__of__(self.root)
            adapter = self._makeOne(plugin)

            plugin.manage_addMapping(user_id=USER_ID,
                                     match_type='equals',
                                     match_string=DOMAIN,
                                     roles=ROLES,
                                    )

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], TITLE)
            user_map = info['map']
            self.assertEqual(len(user_map), 1)
            self.failUnless(USER_ID in user_map)
            match_list = user_map[USER_ID]
            self.assertEqual(len(match_list), 1)
            match = match_list[0]
            self.assertEqual(match['username'], USER_ID)
            self.assertEqual(match['match_type'], 'equals')
            self.assertEqual(match['match_string'], DOMAIN)
            self.assertEqual(match['roles'], ','.join(ROLES))

        def test_export_with_map(self):
            TITLE = 'With Map'
            USER_ID = 'some_user_id'
            DOMAIN = 'host.example.com'
            ROLES = ['foo', 'bar']
            plugin = self._makePlugin('with_map', TITLE).__of__(self.root)
            adapter = self._makeOne(plugin)

            plugin.manage_addMapping(user_id=USER_ID,
                                     match_type='equals',
                                     match_string=DOMAIN,
                                     roles=ROLES,
                                    )

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual(len(context._wrote), 1)
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'plugins/with_map.xml' )
            self._compareDOM(text,
                             _FILLED_DOMAIN_AUTH %
                              (TITLE,
                               USER_ID,
                               DOMAIN,
                               'equals',
                               ','.join(ROLES),
                               USER_ID,
                              ))
            self.assertEqual( content_type, 'text/xml' )

        def test_import_empty(self):
            TITLE = 'With Map'
            USER_ID = 'some_user_id'
            DOMAIN = 'host.example.com'
            ROLES = ['foo', 'bar']
            plugin = self._makePlugin('empty').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/empty.xml'
                          ] = _FILLED_DOMAIN_AUTH % (TITLE,
                                                     USER_ID,
                                                     DOMAIN,
                                                     'equals',
                                                     ','.join(ROLES),
                                                     USER_ID,
                                                    )
            self.assertEqual(plugin.title, '')

            adapter.import_(context, 'plugins', False)

            self.assertEqual(len(plugin._domain_map), 1)
            self.assertEqual(plugin.title, TITLE)

            username, match_list = plugin._domain_map.items()[0]
            self.assertEqual(username, USER_ID)
            self.assertEqual(len(match_list), 1)
            match = match_list[0]
            self.assertEqual(match['username'], USER_ID)
            self.assertEqual(match['match_string'], DOMAIN)
            self.assertEqual(match['match_real'], DOMAIN)
            self.assertEqual(match['match_type'], 'equals')
            self.assertEqual(len(match['roles']), len(ROLES))
            for role in ROLES:
                self.failUnless(role in match['roles'])

        def test_import_without_purge_leaves_existing_users(self):
            TITLE = 'With Map'
            USER_ID = 'some_user_id'
            DOMAIN = 'host.example.com'
            ROLES = ['foo', 'bar']
            plugin = self._makePlugin('with_map', TITLE).__of__(self.root)
            adapter = self._makeOne(plugin)

            plugin.manage_addMapping(user_id=USER_ID,
                                     match_type='equals',
                                     match_string=DOMAIN,
                                     roles=ROLES,
                                    )

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=False)
            context._files['plugins/with_map.xml'] = _EMPTY_DOMAIN_AUTH

            self.assertEqual(len(plugin._domain_map), 1)
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._domain_map), 1)
            self.assertEqual(plugin.title, None)

        def test_import_with_purge_wipes_existing_users(self):
            TITLE = 'With Map'
            USER_ID = 'some_user_id'
            DOMAIN = 'host.example.com'
            ROLES = ['foo', 'bar']
            plugin = self._makePlugin('with_map', TITLE).__of__(self.root)

            adapter = self._makeOne(plugin)

            plugin.manage_addMapping(user_id=USER_ID,
                                     match_type='equals',
                                     match_string=DOMAIN,
                                     roles=ROLES,
                                    )
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=True)
            context._files['plugins/with_map.xml'] = _EMPTY_DOMAIN_AUTH

            self.assertEqual(len(plugin._domain_map), 1)
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin._domain_map), 0)
            self.assertEqual(plugin.title, None)

    class TitleOnlyExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import TitleOnlyExportImport
            return TitleOnlyExportImport

        def _makePlugin(self, id, *args, **kw):
            from OFS.SimpleItem import SimpleItem

            class _Plugin(SimpleItem):
                title = None

                def __init__(self, id, title=None):
                    self._setId(id)
                    if title is not None:
                        self.title = title

            return _Plugin(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_no_title(self):
            plugin = self._makePlugin('simple', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)

        def test__getExportInfo_with_title(self):
            plugin = self._makePlugin('simple', None).__of__(self.root)
            plugin.title = 'Plugin Title'
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], 'Plugin Title')

        def test_export_no_title(self):
            plugin = self._makePlugin('no_title', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/no_title.xml' )
            self._compareDOM( text, _TITLE_ONLY_TEMPLATE_NO_TITLE )
            self.assertEqual( content_type, 'text/xml' )

        def test_export_with_title(self):
            TITLE = 'Plugin Title'
            plugin = self._makePlugin('with_title', None).__of__(self.root)
            plugin.title = TITLE
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/with_title.xml' )
            self._compareDOM( text, _TITLE_ONLY_TEMPLATE % TITLE )
            self.assertEqual( content_type, 'text/xml' )

        def test_import_with_title(self):
            TITLE = 'Plugin Title'
            plugin = self._makePlugin('with_title').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/with_title.xml'
                          ] = _TITLE_ONLY_TEMPLATE % TITLE
            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, TITLE )

        def test_import_no_title(self):
            TITLE = 'Plugin Title'
            plugin = self._makePlugin('no_title').__of__(self.root)
            plugin.title = TITLE
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/no_title.xml'
                          ] = _TITLE_ONLY_TEMPLATE_NO_TITLE

            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, None )

    class DelegatePathExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import DelegatePathExportImport
            return DelegatePathExportImport

        def _makePlugin(self, id, *args, **kw):
            from OFS.SimpleItem import SimpleItem

            class _Plugin(SimpleItem):
                title = None
                delegate_path = ''

                def __init__(self, id, title=None):
                    self._setId(id)
                    if title is not None:
                        self.title = title

            return _Plugin(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.delegate_path = 'path/to/delegate'
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_default(self):
            plugin = self._makePlugin('default').__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(info['delegate_path'], '')

        def test_export_default(self):
            plugin = self._makePlugin('default').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual(len(context._wrote), 1)
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'plugins/default.xml' )
            self._compareDOM(text, _DELEGATE_PATH_TEMPLATE_NO_TITLE % "")
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_explicitly_set(self):
            TITLE = 'Plugin Title'
            DELEGATE_PATH = 'path/to/delegate'
            plugin = self._makePlugin('explicit').__of__(self.root)
            plugin.title = TITLE
            plugin.delegate_path = DELEGATE_PATH
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], TITLE)
            self.assertEqual(info['delegate_path'], DELEGATE_PATH)

        def test_export_explicitly_set(self):
            TITLE = 'Plugin Title'
            DELEGATE_PATH = 'path/to/delegate'
            plugin = self._makePlugin('explicit').__of__(self.root)
            plugin.title = TITLE
            plugin.delegate_path = DELEGATE_PATH
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual(len(context._wrote), 1)
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'plugins/explicit.xml' )
            self._compareDOM(text,
                             _DELEGATE_PATH_TEMPLATE % (TITLE,
                                                        DELEGATE_PATH,
                                                       ))
            self.assertEqual( content_type, 'text/xml' )

        def test_import_with_title(self):
            TITLE = 'Plugin Title'
            DELEGATE_PATH = 'path/to/delegate'
            plugin = self._makePlugin('with_title').__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/with_title.xml'
                          ] = _DELEGATE_PATH_TEMPLATE % (TITLE,
                                                         DELEGATE_PATH,
                                                        )
            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, TITLE )
            self.assertEqual( plugin.delegate_path, DELEGATE_PATH )

        def test_import_no_title(self):
            TITLE = 'Plugin Title'
            DELEGATE_PATH = 'path/to/delegate'
            plugin = self._makePlugin('no_title').__of__(self.root)
            plugin.title = TITLE
            plugin.delegate_path = DELEGATE_PATH
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin)
            context._files['plugins/no_title.xml'
                          ] = _DELEGATE_PATH_TEMPLATE_NO_TITLE % DELEGATE_PATH
            adapter.import_(context, 'plugins', False)

            self.assertEqual( plugin.title, None )
            self.assertEqual( plugin.delegate_path, DELEGATE_PATH )

    class DynamicGroupsPluginExportImportTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluggableAuthService.plugins.exportimport \
                import DynamicGroupsPluginExportImport
            return DynamicGroupsPluginExportImport

        def _makePlugin(self, id, *args, **kw):
            from Products.PluggableAuthService.plugins.DynamicGroupsPlugin \
                import DynamicGroupsPlugin

            return DynamicGroupsPlugin(id, *args, **kw)

        def test_listExportableItems(self):
            plugin = self._makePlugin('lEI').__of__(self.root)
            adapter = self._makeOne(plugin)

            self.assertEqual(len(adapter.listExportableItems()), 0)
            plugin.addGroup('group_id', 'python:1', 'Group Title' )
            self.assertEqual(len(adapter.listExportableItems()), 0)

        def test__getExportInfo_empty(self):
            plugin = self._makePlugin('empty', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], None)
            self.assertEqual(len(info['groups']), 0)

        def test_export_empty(self):
            plugin = self._makePlugin('empty', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len( context._wrote ), 1 )
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual( filename, 'plugins/empty.xml' )
            self._compareDOM( text, _EMPTY_DYNAMIC_GROUPS )
            self.assertEqual( content_type, 'text/xml' )

        def test__getExportInfo_with_groups(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _DYNAMIC_GROUP_INFO:
                plugin.addGroup(g['group_id'],
                                g['predicate'],
                                g['title'],
                                g['description'],
                                g['active'],
                               )

            adapter = self._makeOne(plugin)

            info = adapter._getExportInfo()
            self.assertEqual(info['title'], 'Plugin Title')
            self.assertEqual(len(info['groups']), len(_DYNAMIC_GROUP_INFO))

            for x, y in zip(info['groups'], _DYNAMIC_GROUP_INFO):
                self.assertEqual(x, y)

        def test_export_with_groups(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _DYNAMIC_GROUP_INFO:
                plugin.addGroup(g['group_id'],
                                g['predicate'],
                                g['title'],
                                g['description'],
                                g['active'],
                               )

            adapter = self._makeOne(plugin)
            context = DummyExportContext(plugin)
            adapter.export(context, 'plugins', False)

            self.assertEqual( len(context._wrote), 1)
            filename, text, content_type = context._wrote[ 0 ]
            self.assertEqual(filename, 'plugins/with_groups.xml')
            self._compareDOM(text, _FILLED_DYNAMIC_GROUPS)
            self.assertEqual(content_type, 'text/xml')

        def test_import_empty(self):
            plugin = self._makePlugin('empty', None).__of__(self.root)
            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, encoding='ascii')
            context._files['plugins/empty.xml'] = _FILLED_DYNAMIC_GROUPS
            self.assertEqual(plugin.title, None)

            adapter.import_(context, 'plugins', False)

            found = plugin.listGroupInfo()
            self.assertEqual(len(found), len(_DYNAMIC_GROUP_INFO))
            self.assertEqual(plugin.title, 'Plugin Title')

            for finfo, ginfo in zip(found, _DYNAMIC_GROUP_INFO):
                self.assertEqual(finfo['id'], ginfo['group_id'])
                self.assertEqual(finfo['predicate'], ginfo['predicate'])
                self.assertEqual(finfo['title'], ginfo['title'])
                self.assertEqual(finfo['description'], ginfo['description'])
                self.assertEqual(finfo['active'], ginfo['active'])

        def test_import_without_purge_leaves_existing_users(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _DYNAMIC_GROUP_INFO:
                plugin.addGroup(g['group_id'],
                                g['predicate'],
                                g['title'],
                                g['description'],
                                g['active'],
                               )

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=False)
            context._files['plugins/with_groups.xml'] = _EMPTY_DYNAMIC_GROUPS

            self.assertEqual(len(plugin.listGroupIds()),
                             len(_DYNAMIC_GROUP_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin.listGroupIds()),
                             len(_DYNAMIC_GROUP_INFO))
            self.assertEqual(plugin.title, None)

        def test_import_with_purge_wipes_existing_users(self):

            plugin = self._makePlugin('with_groups').__of__(self.root)
            plugin.title = 'Plugin Title'

            for g in _DYNAMIC_GROUP_INFO:
                plugin.addGroup(g['group_id'],
                                g['predicate'],
                                g['title'],
                                g['description'],
                                g['active'],
                               )

            adapter = self._makeOne(plugin)

            context = DummyImportContext(plugin, purge=True)
            context._files['plugins/with_groups.xml'] = _EMPTY_DYNAMIC_GROUPS

            self.assertEqual(len(plugin.listGroupIds()),
                             len(_DYNAMIC_GROUP_INFO))
            adapter.import_(context, 'plugins', False)
            self.assertEqual(len(plugin.listGroupIds()), 0)
            self.assertEqual(plugin.title, None)

    def test_suite():
        suite = unittest.TestSuite((
            unittest.makeSuite(ZODBUserManagerExportImportTests),
            unittest.makeSuite(ZODBGroupManagerExportImportTests),
            unittest.makeSuite(ZODBRoleManagerExportImportTests),
            unittest.makeSuite(CookieAuthHelperExportImportTests),
            unittest.makeSuite(DomainAuthHelperExportImportTests),
            unittest.makeSuite(TitleOnlyExportImportTests),
            unittest.makeSuite(DelegatePathExportImportTests),
            unittest.makeSuite(DynamicGroupsPluginExportImportTests),
                        ))
        return suite

_EMPTY_ZODB_USERS = """\
<?xml version="1.0" ?>
<zodb-users>
</zodb-users>
"""

_ZODB_USER_INFO = ({'user_id': 'user_1',
                    'login_name': 'user1@example.com',
                    'password': 'password1',
                   },
                   {'user_id': 'user_2',
                    'login_name': 'user2@example.com',
                    'password': 'password2',
                   },
                  )

_FILLED_ZODB_USERS = """\
<?xml version="1.0" ?>
<zodb-users title="Plugin Title">
<user user_id="user_1"
login_name="user1@example.com"
password_hash="%s" />
<user user_id="user_2"
login_name="user2@example.com"
password_hash="%s" />
</zodb-users>
"""

_EMPTY_ZODB_GROUPS = """\
<?xml version="1.0" ?>
<zodb-groups>
</zodb-groups>
"""

_ZODB_GROUP_INFO = ({'group_id': 'group_1',
                     'title': 'Group 1',
                     'description': 'First Group',
                     'principals': ('principal1', 'principal2'),
                    },
                    {'group_id': 'group_2',
                     'title': 'Group 2',
                     'description': 'Second Group',
                     'principals': ('principal1', 'principal3'),
                    },
                   )

_FILLED_ZODB_GROUPS = """\
<?xml version="1.0" ?>
<zodb-groups title="Plugin Title">
<group group_id="group_1" title="Group 1" description="First Group">
<principal principal_id="principal1" />
<principal principal_id="principal2" />
</group>
<group group_id="group_2" title="Group 2" description="Second Group">
<principal principal_id="principal1" />
<principal principal_id="principal3" />
</group>
</zodb-groups>
"""

_EMPTY_ZODB_ROLES = """\
<?xml version="1.0" ?>
<zodb-roles>
</zodb-roles>
"""

_ZODB_ROLE_INFO = ({'role_id': 'role_1',
                    'title': 'Role 1',
                    'description': 'First Role',
                    'principals': ('principal1', 'principal2'),
                   },
                   {'role_id': 'role_2',
                    'title': 'Role 2',
                    'description': 'Second Role',
                    'principals': ('principal1', 'principal3'),
                   },
                  )

_FILLED_ZODB_ROLES = """\
<?xml version="1.0" ?>
<zodb-roles title="Plugin Title">
<role role_id="role_1" title="Role 1" description="First Role">
<principal principal_id="principal1" />
<principal principal_id="principal2" />
</role>
<role role_id="role_2" title="Role 2" description="Second Role">
<principal principal_id="principal1" />
<principal principal_id="principal3" />
</role>
</zodb-roles>
"""

_COOKIE_AUTH_TEMPLATE_NO_TITLE = """\
<?xml version="1.0" ?>
<cookie-auth cookie_name="%s" login_path="%s" />
"""

_COOKIE_AUTH_TEMPLATE = """\
<?xml version="1.0" ?>
<cookie-auth title="%s" cookie_name="%s" login_path="%s" />
"""

_EMPTY_DOMAIN_AUTH = """\
<?xml version="1.0" ?>
<domain-auth>
</domain-auth>
"""

_FILLED_DOMAIN_AUTH = """\
<?xml version="1.0" ?>
<domain-auth title="%s">
 <user user_id="%s">
  <match match_string="%s" match_type="%s" roles="%s" username="%s"/>
 </user>
</domain-auth>
"""

_TITLE_ONLY_TEMPLATE_NO_TITLE = """\
<?xml version="1.0" ?>
<plug-in />
"""

_TITLE_ONLY_TEMPLATE = """\
<?xml version="1.0" ?>
<plug-in title="%s" />
"""

_DELEGATE_PATH_TEMPLATE_NO_TITLE = """\
<?xml version="1.0" ?>
<delegating-plugin delegate_path="%s" />
"""

_DELEGATE_PATH_TEMPLATE = """\
<?xml version="1.0" ?>
<delegating-plugin title="%s" delegate_path="%s" />
"""

_DYNAMIC_GROUP_INFO = ({'group_id': 'group_1',
                        'title': 'Group 1',
                        'predicate': 'python:1',
                        'description': 'First Group',
                        'active': True,
                       },
                       {'group_id': 'group_2',
                        'title': 'Group 2',
                        'predicate': 'python:0',
                        'description': 'Second Group',
                        'active': False,
                       },
                      )

_EMPTY_DYNAMIC_GROUPS = """\
<?xml version="1.0" ?>
<dynamic-groups>
</dynamic-groups>
"""

_FILLED_DYNAMIC_GROUPS = """\
<?xml version="1.0" ?>
<dynamic-groups title="Plugin Title">
<group
    group_id="group_1"
    predicate="python:1"
    title="Group 1"
    description="First Group"
    active="True"
    />
<group
    group_id="group_2"
    predicate="python:0"
    title="Group 2"
    description="Second Group"
    active="False"
    />
</dynamic-groups>
"""

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
