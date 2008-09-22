###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")

import sys


class DifferentiateTemplates(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        
        # Maps of template to class. Does not include IpInterface templates
        tmap = {
            "Fan": "Products.ZenModel.Fan",
            "FCPort": "ZenPacks.zenoss.BrocadeMonitor.FCPort",
            "FileSystem": "Products.ZenModel.FileSystem",
            "FileSystemSnapshot": "ZenPacks.zenoss.NetAppMonitor.NetAppFS",
            "HardDisk": "Products.ZenModel.HardDisk",
            "IpService": "Products.ZenModel.IpService",
            "LTMVirtualServer": "ZenPacks.zenoss.BigIpMonitor.LTMVirtualServer",
            "OSProcess": "Products.ZenModel.OSProcess",
            "PowerSupply": "Products.ZenModel.PowerSupply",
            "RTTProbeJitter": "ZenPacks.zenoss.CiscoMonitor.RTTProbe",
            "SLBVirtualServer": "ZenPacks.zenoss.CiscoMonitor.SLBVirtualServer",
            "TemperatureSensor": "Products.ZenModel.TemperatureSensor",
            "VPNTunnel": "ZenPacks.zenoss.NetScreenMonitor.VPNTunnel",
            "VirtualMachine": "ZenPacks.zenoss.ZenossVirtualHostMonitor.VirtualMachine",
            "WinService": "Products.ZenModel.WinService",
            }
        
        for t in dmd.Devices.getAllRRDTemplates():
            if getattr(t, "targetPythonClass", None): continue
            if not tmap.has_key(t.id): continue
            t.targetPythonClass = tmap[t.id]
        
        # Interfaces are a special case where we really don't know what all of
        # the possible names could be for templates that get bound to them.
        for c in dmd.Devices.getSubComponents(meta_type="IpInterface"):
            for t in c.getRRDTemplates():
                if getattr(t, "targetPythonClass", None): continue
                t.targetPythonClass = "Products.ZenModel.IpInterface"


DifferentiateTemplates()
