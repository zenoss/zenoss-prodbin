##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from os.path import join

import unittest

from Products.DataCollector.Plugins import (
    CoreLoaderFactory,
    PackLoaderFactory,
    _getModulePath,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestWalker(object):
    """
    instead of walking the filesystem, this walker yields a single tuple
    based on the parameters passed in to the initializer
    """

    def __init__(self, package, path, filename):
        self.package = package
        self.path = path
        self.filename = filename

    def walk(self, package):
        assert package == self.package
        yield join(package, self.path), [], [self.filename]


class MixinPluginTest(object):
    def runTest(self):
        loaders = list(self.factory.genLoaders(self.package, "plugins"))
        self.assertEqual(1, len(loaders))
        self.assertEqual(self.package, loaders[0].package)
        self.assertEqual(self.modPath, loaders[0].modPath)
        self.assertEqual(self.pluginName, loaders[0].pluginName)


class CorePluginTest(BaseTestCase, MixinPluginTest):
    """Test the conventions used for core plugins"""

    def afterSetUp(self):
        super(CorePluginTest, self).afterSetUp()
        self.package = "/usr/local/zenoss/Products/DataCollector/plugins"
        walker = TestWalker(self.package, "zenoss/cmd", "df.py")
        self.factory = CoreLoaderFactory(walker)
        self.pluginName = "zenoss.cmd.df"
        self.modPath = self.pluginName


class EggPackPluginTest(BaseTestCase, MixinPluginTest):
    """
    Test the conventions used for zenpack plugins against a simulated
    egg-installed zenpack
    """

    def afterSetUp(self):
        super(EggPackPluginTest, self).afterSetUp()
        self.package = (
            "/usr/local/zenoss/ZenPacks"
            "/ZenPacks.zenoss.LinuxMonitor-1.0.0-py2.4.egg"
            "/ZenPacks/zenoss/LinuxMonitor/modeler/plugins"
        )
        walker = TestWalker(self.package, "zenoss/cmd/linux", "cpuinfo.py")
        modPathPrefix = "ZenPacks.zenoss.LinuxMonitor.modeler.plugins"
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = "zenoss.cmd.linux.cpuinfo"
        self.modPath = ".".join([modPathPrefix, self.pluginName])


class LinkPackPluginTest(BaseTestCase, MixinPluginTest):
    """
    Test the conventions used for zenpack plugins against a simulated
    link-installed zenpack
    """

    def afterSetUp(self):
        super(LinkPackPluginTest, self).afterSetUp()
        self.package = (
            "/home/zenoss/working_copies/enterprise_zenpacks"
            "/ZenPacks.zenoss.AixMonitor/ZenPacks/zenoss"
            "/AixMonitor/modeler/plugins/zenoss/cmd/aix"
        )
        walker = TestWalker(self.package, "zenoss/cmd/aix", "lslpp.py")
        modPathPrefix = "ZenPacks.zenoss.AixMonitor.modeler.plugins"
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = "zenoss.cmd.aix.lslpp"
        self.modPath = ".".join([modPathPrefix, self.pluginName])
        self.lastModName = "plugins"


class GetModulePathTest(unittest.TestCase):
    def test_core(t):
        package = (
            "/opt/zenoss/lib/python2.7/site-packages"
            "/Products/DataCollector/plugins"
        )
        modpath = "zenoss.cmd.linux.memory"
        expected = "Products.DataCollector.plugins.zenoss.cmd.linux.memory"
        actual = _getModulePath(package, modpath)
        t.assertEqual(actual, expected)

    def test_zenpack(t):
        package = (
            "/opt/zenoss/ZenPacks/"
            "/ZenPacks.zenoss.LinuxMonitor-2.3.4-py2.7.egg/"
            "/ZenPacks/zenoss/LinuxMonitor/modeler/plugins"
        )
        modpath = (
            "ZenPacks.zenoss.LinuxMonitor.modeler.plugins."
            "zenoss.cmd.linux.interfaces"
        )
        expected = modpath
        actual = _getModulePath(package, modpath)
        t.assertEqual(actual, expected)
