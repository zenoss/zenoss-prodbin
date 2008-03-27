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
from Products.ZenHub.HubService import threaded
from Products.ZenHub.PBDaemon import translateError

class PingConfig(PerformanceConfig):
    "Support zenping configuration loading"

    @threaded
    @translateError
    def remote_getPingTree(self, root, fallbackIp):
        conn = self.dmd._p_jar._db.open()
        try:
            dmd = conn.root()['Application'].zport.dmd
            return self.getPingTree(dmd, root, fallbackIp)
        finally:
            conn.close()

    def getPingTree(self, dmd, root, fallbackIp):
        me = dmd.Devices.findDevice(root)
        if not me:
            ip = dmd.Networks.findIp(fallbackIp)
            if ip and ip.device():
                me = ip.device()
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
        devices = self.config.getPingDevices()
        self.prepDevices(tree, devices)
        return tree.root


    def prepDevices(self, pingtree, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            if not pingtree.hasDev(device):
              pingtree.addDevice(device)

    def sendDeviceConfig(self, listener, config):
        listener.callRemote('updateConfig')
