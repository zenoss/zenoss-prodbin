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

import logging
log = logging.getLogger("zen.PythonClient")

import Globals

class PythonClient(object):

    def __init__(self, device=None, datacollector=None, plugins=[]):
        self.device = device
        self.hostname = device.id
        self.datacollector = datacollector
        self.plugins = plugins
        self.results = []


    def run(self):
        """Start Python collection.
        """
        for plugin in self.plugins:
            pname = plugin.name()
            log.debug("running collection for plugin %s", pname)
            self.results.append((pname, plugin.collect(self.device, log)))
        self.clientFinished()


    def clientFinished(self):
        log.info("python client finished collection for %s" % self.device.id)
        if self.datacollector:
            self.datacollector.clientFinished(self)


    def getResults(self):
        return self.results
