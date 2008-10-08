###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenStatus import pingtree
from Products.ZenHub.services.PerformanceConfig import PerformanceConfig
from Products.ZenHub.PBDaemon import translateError
from Products.ZenUtils.ZCmdBase import login

class PingConfig(PerformanceConfig):
    "Support zenping configuration loading"

    @translateError
    def remote_getPingTree(self, root, fallbackIp):
        return self.getPingTree(self.dmd, root, fallbackIp)

    def getPingTree(self, dmd, root, fallbackIp):
        pm = dmd.Monitors.getPerformanceMonitor(self.instance)
        me = pm.findDevice(root)
        if not me:
            me = self.lookupByIp(dmd, fallbackIp)
        if me: 
            self.log.info("building pingtree from %s", me.id)
            tree = pingtree.buildTree(me)
        else:
            self.log.critical("ZenPing '%s' not found, "
                              "ignoring network topology.",
                              root)
            tree = pingtree.PingTree(fallbackIp)
            tree.root = pingtree.RouterNode(fallbackIp, root, 0)
            tree.root.addNet(tree, "default", "default")
        config = dmd.Monitors.Performance._getOb(self.instance)
        devices = config.getPingDevices()
        self.prepDevices(tree, devices)
        return tree.root


    def getDeviceConfig(self, device):
        return device


    def lookupByIp(self, dmd, fallbackIp):
        """Try to find the root device by our IP
        """
        ip = dmd.Networks.findIp(fallbackIp)
        if ip and ip.device():
            return ip.device()
        

    def prepDevices(self, pingtree, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            if not pingtree.hasDev(device):
              pingtree.addDevice(device)

    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateConfig')
