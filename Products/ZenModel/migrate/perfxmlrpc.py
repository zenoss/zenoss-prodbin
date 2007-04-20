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
__doc__='''

Add zXmlRpcMonitorIgnore to DeviceClass and XmlRpc to EventClass.

'''
import Migrate

class PerfXmlRpc(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zXmlRpcMonitorIgnore"):
            dmd.Devices._setProperty("zXmlRpcMonitorIgnore", 
                                     False, type="boolean")

        dmd.Events.createOrganizer("/Status/XmlRpc")
        dmd.Events.createOrganizer("/Perf/Snmp")
        dmd.Events.createOrganizer("/Perf/CPU")
        dmd.Events.createOrganizer("/Perf/Interface")
        dmd.Events.createOrganizer("/Perf/Memory")
        dmd.Events.createOrganizer("/Perf/Filesystem")

PerfXmlRpc()

