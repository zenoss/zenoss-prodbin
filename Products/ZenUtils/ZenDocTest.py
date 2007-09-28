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
import doctest
import transaction
import socket
import Globals

from unittest import TestSuite

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.ZenUtils.ZeoConn import ZeoConn


class TestSuiteWithHooks(TestSuite):
    """
    A modified TestSuite that provides hooks for startUp and tearDown methods.
    """
    def run(self, result):
        self.startUp()
        TestSuite.run(self, result)
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
    
    def setUp(self):
        if not self.conn: self.conn = ZeoConn()
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
        if type(mods)!=type([]): mods = [mods]
        self.modules.extend(mods)

    def get_suites(self):
        """
        Returns a doctest.DocTestSuite for each module
        in self.modules.

        Provided for integration with existing unittest framework.
        """
        self.setUp()
        finder = doctest.DocTestFinder(exclude_empty=True)
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

