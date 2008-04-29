###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class BaseClient(object):
    "Define the DataCollector Client interface"

    def __init__(self, device, datacollector):
        self.hostname = None
        if device:
            self.hostname = device.id
        self.device = device
        self.datacollector = datacollector
        self.timeout = None
        self.timedOut = False

    def run(self):
        pass

    def stop(self):
        pass

    def getResults(self):
        return []
    
