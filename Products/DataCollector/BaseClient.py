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

__doc__ = """BaseClient
Base class for the client interface for data collection
"""

class BaseClient(object):
    """
    Define the DataCollector Client interface
    """

    def __init__(self, device, datacollector):
        """
        Initializer

        @param device: remote device to use the datacollector
        @type device: device object
        @param datacollector: performance data collector object
        @type datacollector: datacollector object
        """
        self.hostname = None
        if device:
            self.hostname = device.id
        self.device = device
        self.datacollector = datacollector
        self.timeout = None
        self.timedOut = False

    def run(self):
        """
        Start the data gathering.
        To be implemented by child classes 
        """
        pass

    def stop(self):
        """
        Stopping condition for the collector.
        To be implemented by child classes
        """
        pass

    def getResults(self):
        """
        Return the results of the data collection.
        To be implemented by child classes

        @return: list of results
        @rtype: list of results
        """
        return []

