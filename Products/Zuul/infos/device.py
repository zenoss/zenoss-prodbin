###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.component import adapts
from zope.interface import implements
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenUtils import IpUtil
from Products.Zuul.tree import TreeNode
from Products.Zuul.interfaces import IDeviceOrganizerNode
from Products.Zuul.interfaces import IDeviceOrganizerInfo
from Products.Zuul.interfaces import IDeviceInfo, IDevice
from Products.Zuul.infos import InfoBase, HasEventsInfoMixin, ProxyProperty
from Products.Zuul import getFacade, info
from Products.Zuul.marshalling import TreeNodeMarshaller
from Products.Zuul.utils import catalogAwareImap
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_INFO, SEVERITY_DEBUG

ORGTYPES = {
    'Devices':'DeviceClass',
    'Systems':'Systems',
    'Locations':'Location',
    'Groups':'DeviceGroups'
}

class DeviceOrganizerNode(TreeNode):
    implements(IDeviceOrganizerNode)
    adapts(DeviceOrganizer)

    @property
    def children(self):
        if getattr(self, '_cached_children', None) is None:
            orgs = self._get_object().children()
            self._cached_children = map(lambda x:DeviceOrganizerNode(x, self._root, self), orgs)
        return self._cached_children

    def _count_devices(self):
        if getattr(self, '_cached_count', None) is None:
            count = 0
            for child in self.children:
                count += child._count_devices()
            count += self._get_object().devices.countObjects()
            self._cached_count = count
        return self._cached_count

    @property
    def text(self):
        # need to query the catalog from the permissions perspective of
        # the uid
        numInstances = self._count_devices()
        text = super(DeviceOrganizerNode, self).text
        return {
            'text': text,
            'count': numInstances,
            'description': 'devices'
        }

    # All nodes are potentially branches, just some have no children
    leaf = False


class DeviceOrganizerTreeNodeMarshaller(TreeNodeMarshaller):
    """
    Doesn't get iconCls for each individually. Loads up max sevs for all nodes
    first, then each node can look up its severity from that single query.
    """

    def __init__(self, root):
        super(DeviceOrganizerTreeNodeMarshaller, self).__init__(root)
        self._severities = {}
        self._eventFacade = getFacade('zep')
        self._uuids = {}

    def _getNodeUuid(self, node):
        if node not in self._uuids:
            self._uuids[node] = IGlobalIdentifier(node._object._unrestrictedGetObject()).getGUID()

        return self._uuids[node]

    def _getUuids(self, node):
        uuids = set([self._getNodeUuid(node)])
        if not node.leaf:
            for child in node.children:
                uuids.update(self._getUuids(child))
        return uuids

    @property
    def _allSeverities(self):
        if not self._severities:
            # Get UUIDs for all items in the tree
            uuids = self._getUuids(self.root)
            self._severities = dict(
                (uuid, self._eventFacade.getSeverityName(severity).lower())
                    for (uuid, severity) in self._eventFacade.getWorstSeverity(uuids, ignore=(SEVERITY_INFO, SEVERITY_DEBUG)).iteritems()
            )

        return self._severities

    def _marshalNode(self, keys, node, iconCls=False):
        obj = self.getValues(keys, node)
        if node.leaf:
            obj['leaf'] = True

        if 'uuid' in keys:
            obj['uuid'] = self._getNodeUuid(node)

        if iconCls:
            severity = self._allSeverities.get(self._getNodeUuid(node), 'clear')
            obj['iconCls'] = node.getIconCls(severity)

        obj['children'] = []
        for childNode in node.children:
            obj['children'].append(self._marshalNode(keys, childNode, iconCls=iconCls))
        return obj

    def marshal(self, keys=None, node=None):
        # Remove iconCls key so we don't get its intrinsic value, instead we want to get it in batches
        keys = keys or self.getKeys()
        iconCls = False
        if 'iconCls' in keys:
            iconCls = True
            keys.remove('iconCls')

        return self._marshalNode(keys, node or self.root, iconCls=iconCls)


class DeviceInfo(InfoBase, HasEventsInfoMixin):
    implements(IDeviceInfo)
    adapts(IDevice)

    @property
    def device(self):
        return self._object.id

    def getDevice(self):
        return self.device

    def getIpAddress(self):
        if self._object.manageIp:
            return IpUtil.ipToDecimal(self._object.manageIp)

    def setIpAddress(self, ip=None):
        msg = self._object.setManageIp(ip)
        if msg:
            raise Exception(msg)

    ipAddress = property(getIpAddress, setIpAddress)

    @property
    def ipAddressString(self):
        manageIp = self._object.manageIp
        if manageIp:
            if "%" in manageIp:
                address, interface = manageIp.split("%")
            else:
                address = manageIp
                interface = None
            addr_part = IpUtil.IPAddress(address)
            if interface is None:
                addr_string = "%s" % addr_part
            else:
                addr_string = "%s%%%s" % (addr_part, interface)
        else:
            addr_string = None
        return addr_string

    def getProductionState(self):
        return self._object.convertProdState(self._object.productionState)

    def setProductionState(self, prodState):
        return getFacade('device').setProductionState(self.uid, prodState)

    productionState = property(getProductionState, setProductionState)

    def getPriority(self):
        return self._object.convertPriority(self._object.priority)

    def setPriority(self, priority):
        self._object.setPriority(priority)

    priority = property(getPriority, setPriority)

    def getCollectorName(self):
        return self._object.getPerformanceServerName()

    def setCollector(self, collector):
        self._object.setPerformanceMonitor(collector)

    collector = property(getCollectorName, setCollector)

    def availability(self):
        return self._object.availability().availability

    @property
    def status(self):
        return self._object.getPingStatus()<1

    @property
    def deviceClass(self):
        return info(self._object.deviceClass())

    @property
    def groups(self):
        return info(self._object.groups())

    @property
    def systems(self):
        return info(self._object.systems())

    @property
    def location(self):
        return info(self._object.location())

    @property
    def uptime(self):
        return self._object.uptimeStr()

    @property
    def firstSeen(self):
        return self._object.getCreatedTimeString()

    @property
    def lastChanged(self):
        return self._object.getLastChangeString()

    @property
    def lastCollected(self):
        return self._object.getSnmpLastCollectionString()

    def getComments(self):
        return self._object.comments

    def setComments(self, value):
        self._object.comments = value

    comments = property(getComments, setComments)

    @property
    def links(self):
        return self._object.getExpandedLinks()

    @property
    def locking(self):
        return {
            'updates': self._object.isLockedFromUpdates(),
            'deletion': self._object.isLockedFromDeletion(),
            'events': self._object.sendEventWhenBlocked()
        }

    def getTagNumber(self):
        return self._object.hw.tag

    def setTagNumber(self, value):
        self._object.hw.tag = value

    tagNumber = property(getTagNumber, setTagNumber)

    def getSerialNumber(self):
        return self._object.hw.serialNumber

    def setSerialNumber(self, value):
        self._object.hw.serialNumber = value

    serialNumber = property(getSerialNumber, setSerialNumber)

    @property
    def hwManufacturer(self):
        if self.hwModel is not None:
            return info(self.hwModel._object.manufacturer())

    @property
    def hwModel(self):
        if self._object.hw:
            return info(self._object.hw.productClass())

    @property
    def osManufacturer(self):
        if self.osModel is not None:
            return info(self.osModel._object.manufacturer())

    @property
    def osModel(self):
        if self._object.os:
            return info(self._object.os.productClass())

    @property
    def memory(self):
        return {
            'ram': self._object.hw.totalMemoryString(),
            'swap': self._object.os.totalSwapString()
        }

    def getRackSlot(self):
        return self._object.rackSlot

    def setRackSlot(self, value):
        self._object.rackSlot = value

    rackSlot = property(getRackSlot, setRackSlot)

    def getSnmpSysName(self):
        return self._object.snmpSysName

    def setSnmpSysName(self, value):
        self._object.snmpSysName = value

    snmpSysName = property(getSnmpSysName, setSnmpSysName)

    def getSnmpContact(self):
        return self._object.snmpContact

    def setSnmpContact(self, value):
        self._object.snmpContact = value

    snmpContact = property(getSnmpContact, setSnmpContact)

    def getSnmpLocation(self):
        return self._object.snmpLocation

    def setSnmpLocation(self, value):
        self._object.snmpLocation = value

    snmpLocation = property(getSnmpLocation, setSnmpLocation)

    def getSnmpAgent(self):
        return self._object.snmpAgent

    def setSnmpAgent(self, value):
        self._object.snmpAgent = value

    snmpAgent = property(getSnmpAgent, setSnmpAgent)

    snmpDescr = ProxyProperty('snmpDescr')

    @property
    def snmpCommunity(self):
        return self._object.getProperty('zSnmpCommunity')

    @property
    def snmpVersion(self):
        return self._object.getProperty('zSnmpVer')

    @property
    def icon(self):
        return self._object.getIconPath()



class DeviceOrganizerInfo(InfoBase, HasEventsInfoMixin):
    implements(IDeviceOrganizerInfo)
    adapts(DeviceOrganizer)

    def getName(self):
        return self._object.getOrganizerName()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    @property
    def path(self):
        return self._object.getPrimaryDmdId()

def _removeZportDmd(path):
    if path.startswith('/zport/dmd'):
        path = path[10:]
    return path

