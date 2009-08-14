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

import Globals
import zope.interface

from twisted.internet import defer
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class MyCollector(object):
    zope.interface.implements(ICollector)

    class MyConfigServiceProxy(object):
        def remote_propertyItems(self):
            return defer.succeed({})

        def remote_getDefaultRRDCreateCommand(self):
            return defer.succeed("blah")

        def remote_getThresholdClasses(self):
            return defer.succeed(['Products.ZenModel.MinMaxThreshold'])

        def remote_getCollectorThresholds(self):
            return defer.succeed([])
        
        def remote_getDeviceConfigs(self, devices=[]):
            return defer.succeed([])

        def callRemote(self, methodName, *args):
            if methodName is 'propertyItems':
                return self.remote_propertyItems()
            elif methodName is 'getDefaultRRDCreateCommand':
                return self.remote_getDefaultRRDCreateCommand()
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

class MyConfig(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.attributes = {}

class Test(BaseTestCase):


    def testConfigure(self):
        cfgService = ConfigurationService(MyCollector(), MyConfig())
        cfgService.configure()
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()