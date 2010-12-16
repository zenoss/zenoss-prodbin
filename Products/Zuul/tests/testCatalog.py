###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import unittest
import transaction
import Zope2
from Testing.ZopeTestCase import ZopeLite
from ZODB.POSException import ConflictError
from ZODB.Connection import ConnectionStateError
from AccessControl.SecurityManagement import newSecurityManager
from Products.ZenTestCase.BaseTestCase import ZenossTestCaseLayer
from Products.ZenTestCase.BaseTestCase import PortalGenerator
from Products.ZenTestCase.BaseTestCase import DmdBuilder

class ZenossConcurrencyTestCase(unittest.TestCase):
    layer = ZenossTestCaseLayer

    def build_dmd(self, app):
        gen = PortalGenerator()
        gen.create(app, 'zport', True)
        builder = DmdBuilder(app.zport, 'localhost', 'zenoss', 'zenoss',
                             'event', 3306, 'localhost', '25',
                             '$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT')
        builder.build()
        builder.dmd.ZenUsers.manage_addUser('tester', roles=('Manager',))
        user = app.zport.acl_users.getUserById('tester')
        newSecurityManager(None, user)

    def setUp(self):
        # Make sure transaction still isn't monkeypatched
        transaction.commit = transaction.manager.commit
        app = ZopeLite.app()
        self.db = Zope2.DB
        self.build_dmd(app)
        transaction.commit()
        try:
            app._p_jar.close()
        except ConnectionStateError:
            pass
        self._apps = []

    def tearDown(self):
        for app in self._apps:
            app._p_jar.sync()
            try:
                app._p_jar.close()
            except ConnectionStateError:
                # We're being really polite anyway; this doesn't 
                # matter that much
                pass
        self.db.close()

    def get_connections(self, n=2):
        result = []
        for i in range(n):
            tm = transaction.TransactionManager()
            conn = self.db.open(transaction_manager=tm)
            app = conn.root()['Application']
            self._apps.append(app)
            result.append((tm, app))
        return result


class TestCatalog(ZenossConcurrencyTestCase):

    # Temporarily disabled test due to harness work needed. It isn't testing
    # anything we use anymore so it's ok.
    def _test_conflict_resolution(self):
        (tm1, app1), (tm2, app2) = self.get_connections(n=2)

        # Add a device that'll be in both
        dev = app1.zport.dmd.Devices.createInstance('adevice')
        tm1.commit()
        app2._p_jar.sync()
        self.assert_(getattr(app1.zport.dmd.Devices.devices, 'adevice', None))
        self.assert_(getattr(app2.zport.dmd.Devices.devices, 'adevice', None))

        # Simulate zencatalog in one client by reindexing the device
        app1.zport.global_catalog.catalog_object(dev)
        tm1.commit()

        # Add another device in the other client
        app2.zport.dmd.Devices.createInstance('adevice2')

        # Committing the second connection's transaction will generate a
        # ConflictError somewhere in the catalog. Our resolution should take
        # care of it.
        try:
            tm2.commit()
        except ConflictError, e:
            self.fail('A ConflictError was raised against %s' % e.oid)
        finally:
            app1._p_jar.sync()
            app2._p_jar.sync()

        # Make sure both devices got indexed
        self.assertEqual(len(app1.zport.global_catalog(id='adevice')), 1)
        self.assertEqual(len(app1.zport.global_catalog(id='adevice2')), 1)



def test_suite():
    return unittest.makeSuite(TestCatalog)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
