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

from Products.ZenUtils.ZenScriptBase import ZenScriptBase


class ZenDocTestRunner(object):
    """
    Extracts doctests from the docstrings of a Zenoss module
    and runs them in an environment similar to that of zendmd.

    Example usage:
        zdtr = ZenDocTestRunner()
        from Products import ZenModel
        zdtr.add_modules(ZenModel)
        zdtr.run()
    """
    
    modules = []
    
    def _setup_globals(self):
        """
        Connect to the database and set up the same global
        variables as are available in zendmd.
        """
        zendmd = ZenScriptBase(connect=True)
        dmd = zendmd.dmd
        app = dmd.getPhysicalRoot()
        zport = app.zport
        find = dmd.Devices.findDevice
        devices = dmd.Devices
        sync = dmd._p_jar.sync
        commit = transaction.commit
        abort = transaction.abort
        me = find(socket.getfqdn())
        globs = vars()
        del globs['self']
        self.globals = globs

    def add_modules(self, mods):
        """
        Add Zenoss modules to be tested.

        @param mods: One or more module objects.
        @type mods: module or list
        """
        if type(mods)!=type([]): mods = [mods]
        self.modules.extend(mods)

    def run(self):
        """
        Run the doctests found in the modules added to this instance.

        This method sets up the zendmd global variables, creates a
        test suite for each module that has been added, and runs
        all suites.
        """
        if not hasattr(self, 'globals'): 
            self._setup_globals()
        suite = unittest.TestSuite()
        for mod in self.modules:
            dtsuite = doctest.DocTestSuite(
                mod,
                globs=self.globals,
                optionflags=doctest.NORMALIZE_WHITESPACE
            )
            suite.addTest(dtsuite)
        runner = unittest.TextTestRunner()
        runner.run(suite)

