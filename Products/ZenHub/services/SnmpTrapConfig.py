##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""SnmpTrapConfig

Provides configuration for an OID translation service.
"""

from __future__ import absolute_import, print_function

import json
import logging

from hashlib import md5

from twisted.spread import pb

from Products.ZenHub.HubService import HubService
from Products.Zuul.catalog.interfaces import IModelCatalogTool

log = logging.getLogger("zen.HubService.SnmpTrapConfig")

SNMPV3_USER_ZPROPS = [
    "zSnmpEngineId",
    "zSnmpSecurityName",
    "zSnmpAuthType",
    "zSnmpAuthPassword",
    "zSnmpPrivType",
    "zSnmpPrivPassword",
]


class FakeDevice(object):
    id = "MIB payload"


class User(pb.Copyable, pb.RemoteCopy):
    version = None
    engine_id = None
    username = None
    authentication_type = None  # MD5 or SHA
    authentication_passphrase = None
    privacy_protocol = None  # DES or AES
    privacy_passphrase = None

    def __str__(self):
        fmt = (
            "<User(version={0.version},"
            "engine_id={0.engine_id},"
            "username={0.username},"
            "authentication_type={0.authentication_type},"
            "privacy_protocol={0.privacy_protocol})>"
        )
        return fmt.format(self)


pb.setUnjellyableForClass(User, User)


class SnmpTrapConfig(HubService):
    """
    Configuration service for the zentrap collection daemon.
    """

    def remote_createAllUsers(self):
        cat = IModelCatalogTool(self.dmd)
        brains = cat.search(
            (
                "Products.ZenModel.Device.Device",
                "Products.ZenModel.DeviceClass.DeviceClass",
            )
        )
        users = []
        for brain in brains:
            device = brain.getObject()
            user = self._create_user(device)
            if user is not None:
                users.append(user)
        log.debug("SnmpTrapConfig.remote_createAllUsers %s users", len(users))
        return users

    def remote_getTrapFilters(self, remoteCheckSum):
        currentCheckSum = md5(self.zem.trapFilters).hexdigest()  # noqa S324
        return (
            (None, None)
            if currentCheckSum == remoteCheckSum
            else (currentCheckSum, self.zem.trapFilters)
        )

    def remote_getOidMap(self, remoteCheckSum):
        oidMap = {b.oid: b.id for b in self.dmd.Mibs.mibSearch() if b.oid}
        currentCheckSum = md5(  # noqa S324
            json.dumps(oidMap, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return (
            (None, None)
            if currentCheckSum == remoteCheckSum
            else (currentCheckSum, oidMap)
        )

    def _create_user(self, obj):
        # if v3 and has at least one v3 user property, then we want to
        # create a user
        if obj.getProperty("zSnmpVer", None) != "v3" or not any(
            obj.hasProperty(p) for p in SNMPV3_USER_ZPROPS
        ):
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

    def _objectUpdated(self, object):
        user = self._create_user(object)
        if user:
            for listener in self.listeners:
                listener.callRemote("createUser", user)


if __name__ == "__main__":
    from pprint import pprint
    from Products.ZenHub.ServiceTester import ServiceTester

    class TrapTester(ServiceTester):
        def buildOptions(self):
            ServiceTester.buildOptions(self)
            self.parser.add_option(
                "--resolve",
                dest="request",
                help="Specify a specific OID or name to map "
                "to the name or OID.",
            )
            self.parser.add_option(
                "--exactMatch",
                dest="exactMatch",
                action="store_true",
                default=True,
                help="When resolving to name, use an exact match",
            )
            self.parser.add_option(
                "--fuzzyMatch",
                dest="exactMatch",
                action="store_false",
                help="When resolving to name, don't use an exact match",
            )
            self.parser.add_option(
                "--list",
                dest="list",
                action="store_true",
                default=False,
                help="List all OIDs?",
            )

        def resolve(self):
            name = self.dmd.Mibs.oid2name(
                self.options.request, exactMatch=self.options.exactMatch
            )
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
            print("\t%s => %s" % (config.id, config.oidMap))

        def run(self):
            if self.options.request:
                self.resolve()
            elif self.options.list:
                self.list()
            else:
                self.showDeviceInfo()

    tester = TrapTester(SnmpTrapConfig)
    tester.run()
