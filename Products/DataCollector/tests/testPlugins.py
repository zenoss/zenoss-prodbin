###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from os.path import join
import unittest
from Products.DataCollector.Plugins import CoreLoaderFactory
from Products.DataCollector.Plugins import PackLoaderFactory

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

class BasePluginTest(unittest.TestCase):
    
    def runTest(self):
        loaders = list(self.factory.genLoaders(self.package, 'plugins'))
        self.assertEqual(1, len(loaders))
        self.assertEqual(self.package, loaders[0].package)
        self.assertEqual(self.modPath, loaders[0].modPath)
        self.assertEqual(self.pluginName, loaders[0].pluginName)
        
class CorePluginTest(BasePluginTest):
    "test the conventions used for core plugins"
    
    def setUp(self):
        self.package = '/usr/local/zenoss/Products/DataCollector/plugins'
        walker = TestWalker(self.package, 'zenoss/cmd', 'df.py')
        self.factory = CoreLoaderFactory(walker)
        self.pluginName = 'zenoss.cmd.df'
        self.modPath = self.pluginName
        
class EggPackPluginTest(BasePluginTest):
    """
    test the conventions used for zenpack plugins against a simulated 
    egg-installed zenpack
    """
    
    def setUp(self):
        self.package = '/usr/local/zenoss/ZenPacks' \
                       '/ZenPacks.zenoss.LinuxMonitor-1.0.0-py2.4.egg' \
                       '/ZenPacks/zenoss/LinuxMonitor/modeler/plugins'
        walker = TestWalker(self.package, 'zenoss/cmd/linux', 'cpuinfo.py')
        modPathPrefix = 'ZenPacks.zenoss.LinuxMonitor.modeler.plugins' 
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = 'zenoss.cmd.linux.cpuinfo'
        self.modPath = '.'.join([modPathPrefix, self.pluginName])
        
class LinkPackPluginTest(BasePluginTest):
    """
    test the conventions used for zenpack plugins against a simulated 
    link-installed zenpack
    """
    
    def setUp(self):
        self.package = '/home/zenoss/working_copies/enterprise_zenpacks' \
                       '/ZenPacks.zenoss.AixMonitor/ZenPacks/zenoss' \
                       '/AixMonitor/modeler/plugins/zenoss/cmd/aix'
        walker = TestWalker(self.package, 'zenoss/cmd/aix', 'lslpp.py')
        modPathPrefix = 'ZenPacks.zenoss.AixMonitor.modeler.plugins'
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = 'zenoss.cmd.aix.lslpp'
        self.modPath = '.'.join([modPathPrefix, self.pluginName])
        self.lastModName = 'plugins'
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CorePluginTest))
    suite.addTest(unittest.makeSuite(EggPackPluginTest))
    suite.addTest(unittest.makeSuite(LinkPackPluginTest))
    return suite
    
