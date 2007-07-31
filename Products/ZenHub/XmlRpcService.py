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
from twisted.web import xmlrpc

import types

class XmlRpcService(xmlrpc.XMLRPC):
    # serializable types
    PRIMITIVES = [types.IntType, types.StringType, types.BooleanType,
                  types.DictType, types.FloatType, types.LongType,
                  types.NoneType]

    def __init__(self, dmd):
        xmlrpc.XMLRPC.__init__(self)
        self.dmd = dmd
        self.zem = dmd.ZenEventManager

    def xmlrpc_sendEvent(self, data):
        'XMLRPC requests are processed asynchronously in a thread'
        return self.zem.sendEvent(data)

    def xmlrpc_sendEvents(self, data):
        return self.zem.sendEvents(data)

    def xmlrpc_getDevicePingIssues(self, *unused):
        return self.zem.getDevicePingIssues()
    
    def xmlrpc_getWmiConnIssues(self, *args):
        return self.zem.getWmiConnIssues(*args)

    def xmlrpc_getDeviceWinInfo(self, *args):
        return self.dmd.Devices.Server.Windows.getDeviceWinInfo(*args)

    def xmlrpc_getWinServices(self, *args):
        return self.dmd.Devices.Server.Windows.getWinServices(*args)

    def xmlrpc_applyDataMap(self, devName, datamap, 
                            relname="", compname="", modname=""):
        """Apply a datamap passed as a list of dicts through XML-RPC.
        """
        dev = self.dmd.findDevice(devName)
        adm = ApplyDataMap()
        adm.applyDataMap(dev, datamap, relname=relname,
                         compname=compname, modname=modname)


    def xmlrpc_getConfigs(self, monitor, dstype):
        '''Return the performance configurations for the monitor name and data
        source provided. '''

        def toDict(device, ds):
            '''marshall the fields from the datasource into a dictionary and
            ignore everything that is not a primitive'''

            vals = {}
            for key in ds.__dict__.keys():
                val = ds.__dict__[key]
                if type(val) in XmlRpcService.PRIMITIVES:
                    vals[key] = val

            vals['device'] = device.id
            return vals


        result = []
        
        # get the performance conf (if it exists)
        conf = getattr(self.dmd.Monitors.Performance, monitor, None)
        if conf is None:
            return result

        # loop over devices that use the performance monitor
        for device in conf.devices._objects:
            for template in device.getRRDTemplates():
                for ds in template.getRRDDataSources():
                    if ds.sourcetype == dstype:
                        result.append(toDict(device, ds))

        return result

