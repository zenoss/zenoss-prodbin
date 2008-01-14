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

class PingConfig(PerformanceConfig):


    def remote_getPingTree(self, root, fallbackIp):
        me = self.dmd.Devices.findDevice(root)
        if me: 
            self.log.info("building pingtree from %s", me.id)
            tree = pingtree.buildTree(me)
        else:
            self.log.critical("ZenPing '%s' not found, "
                              "ignoring network topology.",
                              root)
            tree = pingtree.RouterNode(fallbackIp, root, 0)
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
