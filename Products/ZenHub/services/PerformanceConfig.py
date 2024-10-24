##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from pynetsnmp import CONSTANTS, security
from pynetsnmp.twistedsnmp import AgentProxy
from twisted.spread import pb
from zope import component

from Products.ZenHub.errors import translateError
from Products.ZenHub.HubService import HubService
from Products.ZenHub.interfaces import IBatchNotifier
from Products.ZenHub.zodb import onUpdate
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.ZenPack import ZenPack

from .Procrastinator import Procrastinate
from .ThresholdMixin import ThresholdMixin

ATTRIBUTES = (
    "id",
    "manageIp",
    "zMaxOIDPerRequest",
    "zSnmpMonitorIgnore",
    "zSnmpAuthPassword",
    "zSnmpAuthType",
    "zSnmpCommunity",
    "zSnmpCommunities",
    "zSnmpContext",
    "zSnmpDiscoveryPorts",
    "zSnmpPort",
    "zSnmpPrivPassword",
    "zSnmpPrivType",
    "zSnmpSecurityName",
    "zSnmpTimeout",
    "zSnmpTries",
    "zSnmpVer",
    "zSnmpEngineId",
)


class SnmpConnInfo(pb.Copyable, pb.RemoteCopy):
    "A class to transfer the many SNMP values to clients"

    changed = False

    def __init__(self, device):
        "Store the properties from the device"
        for propertyName in ATTRIBUTES:
            setattr(self, propertyName, getattr(device, propertyName, None))
            self.id = device.id

    def __eq__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return False
        if self is other:
            return True
        return all(
            getattr(self, name) == getattr(other, name) for name in ATTRIBUTES
        )

    def __lt__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return NotImplemented
        if self is other:
            return False
        return any(
            getattr(self, name) < getattr(other, name) for name in ATTRIBUTES
        )

    def __le__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return NotImplemented
        if self is other:
            return True
        return not any(
            getattr(self, name) > getattr(other, name) for name in ATTRIBUTES
        )

    def summary(self):
        result = "SNMP info for %s at %s:%s" % (
            self.id,
            self.manageIp,
            self.zSnmpPort,
        )
        result += " timeout: %s tries: %d" % (
            self.zSnmpTimeout,
            self.zSnmpTries,
        )
        result += " version: %s" % (self.zSnmpVer)
        if "3" not in self.zSnmpVer:
            result += " community: %s" % self.zSnmpCommunity
        else:
            result += " securityName: %s" % self.zSnmpSecurityName
            result += " authType: %s" % self.zSnmpAuthType
            result += " privType: %s" % self.zSnmpPrivType
        return result

    def createSession(self, protocol=None):
        """Create a session based on the properties"""
        if "3" in self.zSnmpVer:
            if self.zSnmpPrivType:
                priv = security.Privacy(
                    self.zSnmpPrivType, self.zSnmpPrivPassword
                )
            else:
                priv = None
            if self.zSnmpAuthType:
                auth = security.Authentication(
                    self.zSnmpAuthType, self.zSnmpAuthPassword
                )
            else:
                auth = ()
            sec = security.UsmUser(
                self.zSnmpSecurityName,
                auth=auth,
                priv=priv,
                engineid=self.zSnmpEngineId,
                context=self.zSnmpContext,
            )
        else:
            if "2" in self.zSnmpVer:
                version = CONSTANTS.SNMP_VERSION_2c
            else:
                version = CONSTANTS.SNMP_VERSION_1
            sec = security.Community(self.zSnmpCommunity, version=version)
        p = AgentProxy.create(
            (self.manageIp, self.zSnmpPort),
            security=sec,
            timeout=self.zSnmpTimeout,
            retries=max(self.zSnmpTries - 1, 0),
        )
        p.snmpConnInfo = self
        return p

    def __repr__(self):
        return "<%s for %s>" % (self.__class__, self.id)


pb.setUnjellyableForClass(SnmpConnInfo, SnmpConnInfo)


class PerformanceConfig(HubService, ThresholdMixin):
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.conf = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.pushConfig)
        self._collectorMap = {}
        self._notifier = component.getUtility(IBatchNotifier)

    @translateError
    def remote_propertyItems(self):
        return self.conf.propertyItems()

    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, object, event):
        if object.id == self.instance:
            for listener in self.listeners:
                listener.callRemote("setPropertyItems", object.propertyItems())

    @onUpdate(ZenPack)
    def zenPackUpdated(self, object, event):
        for listener in self.listeners:
            try:
                listener.callRemote(
                    "updateThresholdClasses", self.remote_getThresholdClasses()
                )
            except Exception:
                self.log.warning(
                    "Error notifying a listener of new threshold classes"
                )
