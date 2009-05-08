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
import Globals
import os.path

from Products.DataCollector.Plugins import PluginLoader, CoreImporter

here = lambda *x:os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)
TEST_PACKAGE = here('plugins')

class ImportPlugins(unittest.TestCase):

    def test_simple(self):
        """
        A trivial collector plugin.
        """
        loader = PluginLoader(here('plugins'), 'zenoss.noimports',
                              'plugins', CoreImporter())
        # We just care that it doesn't raise anything
        plugin = loader.create()
        self.assertEqual(plugin.MARKER, 'abcdefg')

    def test_internal_imports(self):
        """
        Collector plugin that does imports from outside the module
        """
        loader = PluginLoader(here('plugins'), 'zenoss.withimports',
                              'plugins', CoreImporter())
        plugin = loader.create()
        self.assert_(plugin.get_re() is not None)

    def test_other_pkg(self):
        """
        Import similar dotted names from different packages.
        """
        loader1 = PluginLoader(here('plugins'), 'zenoss.noimports',
                               'plugins', CoreImporter())
        loader2 = PluginLoader(here('otherplugins'), 'zenoss.noimports'                      ,
                               'plugins', CoreImporter())
        self.assertEqual(loader1.create().MARKER, 'abcdefg')
        self.assertEqual(loader2.create().MARKER, 'gfedcba')



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ImportPlugins))
    return suite
