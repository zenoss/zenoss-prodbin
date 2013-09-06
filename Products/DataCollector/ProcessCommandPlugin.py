##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from pprint import pformat

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class ProcessCommandPlugin(CommandPlugin):
    """
    Base class for Linux and AIX command plugins for parsing ps command output
    and modeling processes.
    """
    
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    classname = "createFromObjectMap"
    
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

        relMap = self.relMap()
        for line in self._filterLines(results.splitlines()):
            # Blank lines are possible. Skip them. (ZEN-798)
            if not line.strip():
                continue
            
            om = self.objectMap({"processText": line.strip()})
            relMap.append(om)
            
        log.debug("First three modeled processes:\n%s" % 
                pformat(relMap.maps[:3]))
                
        return relMap
