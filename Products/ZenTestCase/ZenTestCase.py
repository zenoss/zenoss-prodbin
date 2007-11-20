###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
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
from Products.ZenUtils.ZeoConn import ZeoConn
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager


class ZenTestCase(unittest.TestCase):
    """
    A modified TestCase object providing a connection to ZEO and the
    context of zendmd.
    """

    def _setUpZendmdContext(self):
        self.conn = ZeoConn()
        self._login()
        self.app = self.conn.app
        self.dmd = self.app.zport.dmd
        find = self.dmd.Devices.findDevice
        self.globals = dict( dmd = self.dmd
                           , app = self.app
                           , find = find
                           , sync = self.dmd._p_jar.sync
                           , commit = transaction.commit
                           , abort = transaction.abort
                           )

    def _login(self, name='admin', userfolder=None):
        if userfolder is None:
            userfolder = self.conn.app.acl_users
        user = userfolder.getUserById(name)
        if user is None: return
        if not hasattr(user, 'aq_base'):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)
    
    def _logout(self):
        noSecurityManager()

    def _tearDownZendmdContext(self):
        transaction.abort()
        self._logout()
        self.conn.closedb()

    def __call__(self, results=None):
        """
        A wrapper for the TestCase __call__, doing the DB connection setup,
        injecting our namespace into the test method, and ensuring
        connection cleanup.
        """
        self._setUpZendmdContext()
        testMethod = getattr(self, self._TestCase__testMethodName)
        namespace = globals().copy()
        namespace.update(self.globals)
        try:
            testMethod.im_func.func_globals.update(namespace)
            super(ZenTestCase, self).__call__(results)
        finally:
            self._tearDownZendmdContext()


