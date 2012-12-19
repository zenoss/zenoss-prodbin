##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = '''SnmpTrapConfig

Provides configuration for an OID translation service.
'''

import logging
log = logging.getLogger('zen.HubService.SnmpTrapConfig')

import Globals

from twisted.spread import pb
from twisted.internet import defer

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenHub.zodb import onUpdate, onDelete

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.MibBase import MibBase
from Products.Zuul.interfaces import ICatalogTool

SNMPV3_USER_ZPROPS = ["zSnmpEngineId",
                      "zSnmpSecurityName",            
                      "zSnmpAuthType",
                      "zSnmpAuthPassword",
                      "zSnmpPrivType",
                      "zSnmpPrivPassword",
                     ]

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
        fmt = "<User(version={0.version},engine_id={0.engine_id},username={0.username},authentication_type={0.authentication_type},privacy_protocol={0.privacy_protocol})>"
        return fmt.format(self)
pb.setUnjellyableForClass(User, User)

class SnmpTrapConfig(CollectorConfigService):

    # Override _notifyAll, notifyAffectedDevices, _filterDevice and 
    # _filterDevicesOnly to guarantee that only one MibConfigTask is ever 
    # sent down to zentrap.

    def _notifyAll(self, object):
        pass

    @onUpdate(None) # Matches all
    def notifyAffectedDevices(self, object, event):
        pass

    def _filterDevice(self, device):
        return device.id == FakeDevice.id

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

        return proxy

    def _create_user(self, obj):
        # if v3 and has at least one v3 user property, then we want to
        # create a user
        if obj.getProperty("zSnmpVer", None) != "v3" or not any(
                            obj.hasProperty(p) for p in SNMPV3_USER_ZPROPS):
            return
        user = User()
        user.version = int(obj.zSnmpVer[1])
        user.engine_id = obj.zSnmpEngineId
        user.username = obj.zSnmpSecurityName
        user.authentication_type = obj.zSnmpAuthType
        user.authentication_passphrase = obj.zSnmpAuthPassword
        user.privacy_protocol = obj.zSnmpPrivType
        user.privacy_passphrase = obj.zSnmpPrivPassword
        return user

    def remote_createAllUsers(self):
        cat = ICatalogTool(self.dmd)
        brains = cat.search(("Products.ZenModel.Device.Device", "Products.ZenModel.DeviceClass.DeviceClass"))
        users = []
        for brain in brains:
            device = brain.getObject()
            user = self._create_user(device)
            if user is not None:
                users.append(user)
        fmt = 'SnmpTrapConfig.remote_createAllUsers {0} users'
        log.debug(fmt.format(len(users)))
        return users

    def _objectUpdated(self, object):
        user = self._create_user(object)
        if user:
            for listener in self.listeners: 
                listener.callRemote('createUser', user)

    @onUpdate(DeviceClass)
    def deviceClassUpdated(self, object, event):
        self._objectUpdated(object)

    @onUpdate(Device)
    def deviceUpdated(self, object, event):
        self._objectUpdated(object)

    @onUpdate(MibBase)
    def mibsChanged(self, device, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')

    @onDelete(MibBase)
    def mibsDeleted(self, device, event):
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')


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
