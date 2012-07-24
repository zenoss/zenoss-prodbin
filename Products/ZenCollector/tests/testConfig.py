##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import zope.component
import zope.interface

from twisted.internet import defer
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenCollector.config import ConfigurationProxy
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences


class MyCollector(object):
    zope.interface.implements(ICollector)

    class MyConfigServiceProxy(object):
        def remote_propertyItems(self):
            return defer.succeed({"name":"foobar", "foobar":"abcxyz"})

        def remote_getThresholdClasses(self):
            return defer.succeed(['Products.ZenModel.FooBarThreshold'])

        def remote_getCollectorThresholds(self):
            return defer.succeed(['yabba dabba do', 'ho ho hum'])
        
        def remote_getDeviceConfigs(self, devices=[]):
            return defer.succeed(['hmm', 'foo', 'bar'])

        def callRemote(self, methodName, *args):
            if methodName is 'getConfigProperties':
                return self.remote_propertyItems()
            elif methodName is 'getThresholdClasses':
                return self.remote_getThresholdClasses()
            elif methodName is 'getCollectorThresholds':
                return self.remote_getCollectorThresholds()
            elif methodName is 'getDeviceConfigs':
                return self.remote_getDeviceConfigs(args)

    def getRemoteConfigServiceProxy(self):
        return MyCollector.MyConfigServiceProxy()
    
    def configureRRD(self, rrdCreateCommand, thresholds):
        pass

class Dummy(object):
    pass

class MyPrefs(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = "testcollector"
        self.options = Dummy()
        self.options.monitor = "localhost"

class TestConfig(BaseTestCase):
    def setUp(self):
        zope.component.provideUtility(MyCollector(), ICollector)

    def testPropertyItems(self):
        def validate(result):
            self.assertEquals(result['name'], "foobar")
            self.assertEquals(result['foobar'], "abcxyz")
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getPropertyItems(prefs)
        d.addBoth(validate)
        return d

    def testThresholdClasses(self):
        def validate(result):
            self.assertTrue('Products.ZenModel.FooBarThreshold' in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getThresholdClasses(prefs)
        d.addBoth(validate)
        return d

    def testThresholds(self):
        def validate(result):
            self.assertTrue('yabba dabba do' in result)
            self.assertTrue('ho ho hum' in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getThresholds(prefs)
        d.addBoth(validate)
        return d

    def testConfigProxies(self):
        def validate(result):
            self.assertTrue('hmm' in result)
            self.assertFalse('abcdef' in result)
            return result

        cfgService = ConfigurationProxy()
        prefs = MyPrefs()

        d = cfgService.getConfigProxies(prefs)
        d.addBoth(validate)
        return d

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestConfig))
    return suite
