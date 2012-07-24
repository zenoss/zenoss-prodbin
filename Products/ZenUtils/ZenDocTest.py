##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
import doctest
import transaction
import socket
import Globals

import zope.component
from zope.traversing.adapters import DefaultTraversable

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.ZenUtils.ZeoConn import ZeoConn


class TestSuiteWithHooks(unittest.TestSuite):
    """
    A modified TestSuite that provides hooks for startUp and tearDown methods.
    """
    def run(self, result):
        self.startUp()
        unittest.TestSuite.run(self, result)
        self.tearDown()

    def startUp(self):
        pass

    def tearDown(self):
        pass


class ZenDocTestRunner(object):
    """
    Extracts doctests from the docstrings of a Zenoss module
    and runs them in an environment similar to that of zendmd.

    Example usage:
        zdtr = ZenDocTestRunner()
        zdtr.add_modules("Products.ZenModel.ZenModelBase")
        zdtr.run()
    """

    modules = []
    conn = None

    def _find_relstorage_adapter_config(self):
        from App.config import getConfiguration
        zope_config = getConfiguration()
        for db in zope_config.databases:
            if db.name == 'main':
                return db.config.storage.config.adapter.config

    def setUp(self):
        import Products.ZenossStartup
        from Products.Five import zcml
        zcml.load_site()

        zope.component.provideAdapter(DefaultTraversable, (None,))
        if not self.conn:
            adapter_config = self._find_relstorage_adapter_config()
            if adapter_config:
                self.conn = ZeoConn(zodb_host=adapter_config.host,
                        zodb_port=adapter_config.port,
                        zodb_user=adapter_config.user,
                        zodb_password=adapter_config.passwd,
                        zodb_db=adapter_config.db,
                        zodb_socket=adapter_config.unix_socket)
            else:
                self.conn = ZeoConn()

        self.app = self.conn.app
        self.login()
        self.dmd = self.app.zport.dmd
        find = self.dmd.Devices.findDevice
        self.globals = dict(
            app = self.app,
            zport = self.app.zport,
            dmd = self.dmd,
            find = find,
            devices = self.dmd.Devices,
            sync = self.dmd._p_jar.sync,
            commit = transaction.commit,
            abort = transaction.abort,
            me = find(socket.getfqdn())
        )

    def tearDown(self):
        self.logout()
        self.conn.closedb()

    def login(self, name='admin', userfolder=None):
        '''Logs in.'''
        if userfolder is None:
            userfolder = self.app.acl_users
        user = userfolder.getUserById(name)
        if user is None: return
        if not hasattr(user, 'aq_base'):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)

    def logout(self):
        noSecurityManager()

    def doctest_setUp(self, testObject):
        self.login()
        self.globals['sync']()
        testObject.globs.update(self.globals)

    def doctest_tearDown(self, testObject):
        self.logout()
        testObject.globs['abort']()
        self.globals['sync']()

    def add_modules(self, mods):
        """
        Add Zenoss modules to be tested.

        @param mods: One or more module objects or dotted names.
        @type mods: module or list
        """
        if not isinstance(mods, list): mods = [mods]
        self.modules.extend(mods)

    def get_suites(self):
        """
        Returns a doctest.DocTestSuite for each module
        in self.modules.

        Provided for integration with existing unittest framework.
        """
        self.setUp()
        doctest.DocTestFinder(exclude_empty=True)
        suites = []
        for mod in self.modules:
            try:
                dtsuite = doctest.DocTestSuite(
                    mod,
                    optionflags=doctest.NORMALIZE_WHITESPACE,
                    setUp = self.doctest_setUp,
                    tearDown = self.doctest_tearDown
                )
            except ValueError:
                pass
            else:
                suites.append(dtsuite)
        return suites

    def run(self):
        """
        Run the doctests found in the modules added to this instance.

        This method sets up the zendmd global variables, creates a
        test suite for each module that has been added, and runs
        all suites.
        """
        suite = unittest.TestSuite()
        for dtsuite in self.get_suites():
            suite.addTest(dtsuite)
        runner = unittest.TextTestRunner()
        runner.run(suite)
        self.tearDown()
