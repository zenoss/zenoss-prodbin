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

from Products.DataCollector.plugins.CollectorPlugin import CollectorPlugin

class WMIPlugin(CollectorPlugin):
    """
    A WMIPlugin defines a native Python collection routine and a parsing
    method to turn the returned data structure into a datamap. A valid
    WMIPlugin must implement the process method.
    """
    transport = "wmi"
    deviceProperties = CollectorPlugin.deviceProperties + (
        'zWmiMonitorIgnore', 
        'zWinUser',
        'zWinPassword',
        'zWinEventlogMinSeverity',
    )
    
    def condition(self, device, log):
        return not getattr(device, 'zWmiMonitorIgnore', True)

    def copyDataToProxy(self, device, proxy):
        for prop in self.deviceProperties:
            if hasattr(device, prop):
                setattr(proxy, prop, getattr(device, prop))
        # Do any other prep of plugin here
        setattr(proxy, 'lastChange', getattr(device, '_lastChange', ''))

    def queries(self):
        raise NotImplementedError
    
    def preprocess(self, results, log):
        if isinstance(results, Exception):
            log.error(results)
            return None
        return results

