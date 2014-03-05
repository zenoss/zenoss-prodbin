##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from pprint import pformat

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin
from Products.ZenModel.OSProcessMatcher import buildObjectMapData


class ProcessCommandPlugin(CommandPlugin):
    """
    Base class for Linux and AIX command plugins for parsing ps command output
    and modeling processes.
    """
    
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    maptype = "OSProcessMap"
    deviceProperties = CommandPlugin.deviceProperties + ('osProcessClassMatchData',)
    
    def _filterLines(self, lines):
        """
        Filter out any unwanted lines.  The base implementation returns all
        the lines.
        """
        return lines

    def process(self, device, results, log):
        log.info('Processing %s for device %s', self.name(), device.id)
        if not results:
            log.error("Unable to get data for %s -- skipping model",
                      device.id)
            return None

        psOutputLines = self._filterLines(results.splitlines())

        cmds = map(lambda(s):s.strip(), psOutputLines)
        cmds = filter(lambda(s):s, cmds)
        rm = self.relMap()
        matchData = device.osProcessClassMatchData
        rm.extend(map(self.objectMap, buildObjectMapData(matchData, cmds)))
        return rm
