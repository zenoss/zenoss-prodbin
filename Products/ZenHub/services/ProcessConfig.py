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
#! /usr/bin/env python 

from PerformanceConfig import PerformanceConfig
from ZODB.POSException import POSError

class ProcessConfig(PerformanceConfig):

    def getProcessStatus(self, device=None):
        "Get the known process status from the Event Manager"
        from Products.ZenEvents.ZenEventClasses import Status_OSProcess
        down = {}
        conn = self.zem.connect()
        try:
            curs = conn.cursor()
            query = ("SELECT device, component, count"
                    "  FROM status"
                    " WHERE eventClass = '%s'" % Status_OSProcess)
            if device:
                query += " AND device = '%s'" % device
            curs.execute(query)
            for device, component, count in curs.fetchall():
                down[device] = (component, count)
        finally:
            self.zem.close(conn)
        result = []
        for dev in self.config.devices():
            try:
                component, count = down[dev.id]
                result.append( (dev.id, component, count) )
            except KeyError:
                pass
        return result


    def getOSProcessConf(self, devices = None):
        'Get the OS Process configuration for all devices.'
        result = []
        for dev in self.config.devices():
            if devices and dev.id not in devices:
                continue
            dev = dev.primaryAq()
            try:
                procinfo = dev.getOSProcessConf()
                if procinfo:
                    result.append(procinfo)
            except POSError: raise
            except:
                self.log.exception("device %s", dev.id)
        return result


    def remote_getOSProcessConf(self, devices=None):
        return self.getOSProcessConf(devices)


    def remote_getProcessStatus(self, devices=None):
        return self.getProcessStatus(devices)


    def getDeviceConfig(self, device):
        return device.getOSProcessConf()


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDevice', config)



