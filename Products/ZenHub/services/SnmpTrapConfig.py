###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = '''SnmpTrapConfig

Provides configuration for an OID translation service.
'''

import logging
log = logging.getLogger('zen.HubService.SnmpTrapConfig')

import Globals

from twisted.spread import pb

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenHub.zodb import onUpdate, onDelete

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.MibBase import MibBase
from Products.Zuul.interfaces import ICatalogTool

class FakeDevice(object):
    id = 'MIB payload'

class User(pb.Copyable, pb.RemoteCopy):
    version = None
    engine_id = None
    username = None
    authentication_type = None # MD5 or SHA
    authentication_passphrase = None
    privacy_protocol = None # DES or AES
    privacy_passphrase = None
    def __str__(self):
        fmt = "<User{version=%s,engine_id=%s,username=%s,authentication_type=%s,authentication_passphrase=%s,privacy_protocol=%s,privacy_passphrase=%s}>"
        args = (self.version,
                self.engine_id,
                self.username,
                self.authentication_type,
                self.authentication_passphrase,
                self.privacy_protocol,
                self.privacy_passphrase)
        return fmt % args
pb.setUnjellyableForClass(User, User)

class SnmpTrapConfig(CollectorConfigService):
    
    def _filterDevices(self, deviceList):
        return [ FakeDevice() ]

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = 3600
        proxy.name = "SNMP Trap Configuration"
        proxy.device = device.id

        # Gather all OID -> Name mappings from /Mibs catalog
        proxy.oidMap = dict(
                       (b.oid, b.id) for b in self.dmd.Mibs.mibSearch() if b.oid
                       )

        def gen_users():
            cat = ICatalogTool(self.dmd)
            for brains in cat.search("Products.ZenModel.Device.Device"):
                device = brains.getObject()
                log.debug("gen_users: creating user from device: %s" % device.id)
                user = User()
                user.version = int(device.zSnmpVer[1])
                if user.version == 3:
                    user.engine_id = device.zSnmpEngineId
                    user.username = device.zSnmpSecurityName
                    user.authentication_type = device.zSnmpAuthType
                    user.authentication_passphrase = device.zSnmpAuthPassword
                    user.privacy_protocol = device.zSnmpPrivType
                    user.privacy_passphrase = device.zSnmpPrivPassword
                yield user

        proxy.users = list(gen_users())

        return proxy

    @onUpdate(DeviceClass)
    def mibsChanged(self, object, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')
        self._procrastinator.doLater()

    @onUpdate(Device)
    def mibsChanged(self, object, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')
        self._procrastinator.doLater()

    @onUpdate(MibBase)
    def mibsChanged(self, object, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')
        self._procrastinator.doLater()

    @onDelete(MibBase)
    def mibsDeleted(self, object, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')
        self._procrastinator.doLater()


if __name__ == '__main__':
    from pprint import pprint
    from Products.ZenHub.ServiceTester import ServiceTester

    class TrapTester(ServiceTester):
        def buildOptions(self):
            ServiceTester.buildOptions(self)
            self.parser.add_option('--resolve', dest='request',
                               help="Specify a specific OID or name to map to the name or OID.")
            self.parser.add_option('--exactMatch', dest='exactMatch',
                                   action='store_true', default=True,
                               help="When resolving to name, use an exact match")
            self.parser.add_option('--fuzzyMatch', dest='exactMatch',
                                   action='store_false',
                               help="When resolving to name, don't use an exact match")
            self.parser.add_option('--list', dest='list',
                                   action='store_true', default=False,
                               help="List all OIDs?")

        def resolve(self):
            name = self.dmd.Mibs.oid2name(self.options.request,
                                          exactMatch=self.options.exactMatch)
            if name:
                log.info("\t%s => %s", self.options.request, name)

            oid = self.dmd.Mibs.name2oid(self.options.request)
            if oid:
                log.info("\t%s => %s", self.options.request, oid)

        def list(self):
            dev = FakeDevice()
            proxy = self.service._createDeviceProxy(dev)
            pprint(proxy.oidMap)

        def printer(self, config):
            print "\t%s => %s" % (config.id, config.oidMap)

        def run(self):
            if self.options.request:
                self.resolve()
            elif self.options.list:
                self.list()
            else:
                self.showDeviceInfo()

    tester = TrapTester(SnmpTrapConfig)
    tester.run()

