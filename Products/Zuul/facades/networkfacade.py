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

import logging
from itertools import imap

from Acquisition import aq_parent
from zope.interface import implements

from Products.Jobber.jobs import ShellCommandJob
from Products.ZenUtils.Utils import binPath
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade, INetworkFacade
from Products.Zuul.interfaces import IInfo, ICatalogTool
from Products.Zuul.tree import SearchResults

log = logging.getLogger('zen.NetworkFacade')


class NetworkFacade(TreeFacade):
    implements(INetworkFacade, ITreeFacade)

    def addSubnet(self, newSubnet, contextUid):
        return self._root.restrictedTraverse(contextUid).createNet(newSubnet)

    def findSubnet(self, netip, netmask, contextUid):
        """
        Try to find a subnet. Using the netip and netmask first try to find
        an existing subnet. If nothing found, try to find the existing subnet to
        which the ip belongs. If a subnet is found, compare the existing subnet's
        mask with netmask. If they are the same, then the subnet that
        the ip matched is returned.

        if 7.0.0.0/8 exists, adding 7.1.2.3/8 will find 7.0.0.0. Because the
        netmasks match, the 7.0.0.0/8 IpNetwork obj will be returned.

        Called by NetworkRouter.addNode

        @param netip: network ip
        @type netip: string
        @param netmask: network mask
        @type netmask: integer
        @param contextUid:
        @type contextUid: string
        @todo: investigate IPv6 issues
        """

        if type(netmask) is not int:
            raise TypeError('Netmask must be an integer')

        netRoot = self._root.restrictedTraverse(contextUid).getNetworkRoot()
        foundNet = netRoot.findNet(netip, netmask)

        if foundNet:
            return foundNet

        gotNet = netRoot.getNet(netip)
        if gotNet and gotNet.netmask == netmask:
            return gotNet

        return None

    def deleteSubnet(self, uid):
        toDel = self._dmd.restrictedTraverse(uid)
        aq_parent(toDel)._delObject(toDel.id)
        return True

    def getIpAddresses(self, limit=0, start=0, sort='ipAddress', dir='DESC',
              params=None, uid=None, criteria=()):

        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'

        brains = cat.search("Products.ZenModel.IpAddress.IpAddress",
                            start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        objs = imap(unbrain, brains)
        infos = imap(IInfo, objs)
        # convert to info objects
        return SearchResults(infos, brains.total, brains.hash_)

    def discoverDevices(self, uid):
        """
        Discover devices on input subnetwork
        """
        ip = '/'.join(self._dmd.restrictedTraverse(uid).getPrimaryPath()[4:])
        orgroot = self._root.restrictedTraverse(uid).getNetworkRoot()

        organizer = orgroot.getOrganizer(ip)
        if organizer is None:
            log.error("Couldn't obtain a network entry for '%s' "
                        "-- does it exist?" % ip)
            return False

        zDiscCommand = getattr(organizer, "zZenDiscCommand", None)
        if zDiscCommand:
            from Products.ZenUtils.ZenTales import talesEval
            cmd = talesEval('string:' + zDiscCommand, organizer).split(" ")
        else:
            cmd = ["zendisc", "run", "--net", organizer.getNetworkName()]
            if getattr(organizer, "zSnmpStrictDiscovery", False):
                cmd += ["--snmp-strict-discovery"]
            if getattr(organizer, "zPreferSnmpNaming", False):
                cmd += ["--prefer-snmp-naming"]
        zd = binPath('zendisc')
        zendiscCmd = [zd] + cmd[1:]
        return self._dmd.JobManager.addJob(ShellCommandJob, zendiscCmd)

    @property
    def _root(self):
        return self._dmd.Networks

    @property
    def _instanceClass(self):
        return "Products.ZenModel.IpAddress.IpAddress"

    def _getSecondaryParent(self, obj):
        return obj

    def removeIpAddresses(self, uids):
        """
        Removes every ip address specified by uids that are
        not attached to any device
        @type  uids: Array of Strings
        @param uids: unique identfiers of the ip addresses to delete
        @rtype:   tuple
        @return:  tuple of the number of deleted ip addresses and the error
        """
        removeCount = 0
        errorCount = 0
        for uid in uids:
            ip = self._getObject(uid)
            # there is an interface do not delete it
            if ip.interface():
                errorCount += 1
                continue
            # remove it from the relationship
            parent = aq_parent(ip)
            parent._delObject(ip.id)
            removeCount += 1
        return removeCount, errorCount


class Network6Facade(NetworkFacade):

    @property
    def _root(self):
        return self._dmd.getDmdRoot("IPv6Networks")

