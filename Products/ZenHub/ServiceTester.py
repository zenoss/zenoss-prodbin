###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """ServiceTester

Simple utility class for testing out zenhub services.
Sample usage (at the bottom of a service):

if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(PingPerformanceConfig)
    def printer(config):
        for ip in config.monitoredIps:
            print '\t', ip
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

Note that the service instance can be found as an attribute
on the tester object.

ie tester.service == PingPerformanceConfig(dmd, 'localhost')
"""

from pprint import pprint
import logging
log = logging.getLogger('zen.ServiceTester')

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase


class ServiceTester(ZCmdBase):
    doesLogging = False

    def __init__(self, Klass):
        ZCmdBase.__init__(self, False, False, False)
        # It's super annoying to try to figure out how to get the
        # zenhub service to drop into debug mode.  Use the following.
        self.setLogLevel(10)
        logging.basicConfig()
        self.service = Klass(self.dmd, self.options.monitor)

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--monitor', dest='monitor', default='localhost',
                               help="Specify the collector to collect against.")
        self.parser.add_option('-d', '--device', dest='device',
                               help="Show the configs for a single device")

    def setLogLevel(self, level=10):
        """
        Change the logging level to allow for more insight into the
        in-flight mechanics of Zenoss.

        @parameter level: logging level at which messages display (eg logging.INFO)
        @type level: integer
        """
        rootlog = logging.getLogger()
        rootlog.setLevel(level)
        for handler in rootlog.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def pprint(self, arg):
        pprint(arg)

    def showDeviceInfo(self):
        if self.options.device:
            name = self.options.device
            config = self.service.remote_getDeviceConfigs([name])
            if config:
                print "Config for %s =" % name
                self.printDeviceProxy(config[0])
            else:
                log.warn("No configs found for %s", name)
        else:
            devices = sorted([x.id for x in self.service.remote_getDeviceConfigs()])
            print "Device list = %s" % devices

    def printDeviceProxy(self, proxy):
        """
        Device proxies don't report their interal state very well. This
        should be overwritten by the zenhub service writer.
        """
        pprint(proxy)
