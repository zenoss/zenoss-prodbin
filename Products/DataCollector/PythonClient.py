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

from BaseClient import BaseClient
from twisted.internet.defer import Deferred, DeferredList
from twisted.python.failure import Failure

class PythonClient(BaseClient):

    def __init__(self, device=None, datacollector=None, plugins=[]):
        BaseClient.__init__(self, device, datacollector)
        self.hostname = device.id
        self.plugins = plugins
        self.results = []


    def run(self):
        """Start Python collection.
        """
        deferreds = []
        for plugin in self.plugins:
            log.debug("running collection for plugin %s", plugin.name())
            r = plugin.collect(self.device, log)
            if isinstance(r, Deferred):
                deferreds.append(r)
                r.addBoth(self.collectComplete, plugin)
            else:
                log.debug("Results for %s: %s", plugin.name(), str(r))
                self.results.append((plugin, r))
        
        dl = DeferredList(deferreds)
        dl.addCallback(self.collectComplete, None)


    def collectComplete(self, r, plugin):
        if plugin is None:
            self.clientFinished()
            return

        if isinstance(r, Failure):
            log.warn("Error in %s: %s", plugin.name(), r.getErrorMessage())
        else:
            log.debug("Results for %s: %s", plugin.name(), str(r))
            self.results.append((plugin, r))


    def clientFinished(self):
        log.info("python client finished collection for %s" % self.device.id)
        if self.datacollector:
            self.datacollector.clientFinished(self)


    def getResults(self):
        return self.results
