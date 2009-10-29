###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


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
            words = line.split()
            
            relMap.append(self.objectMap({
                "procName": words[0],
                "parameters": " ".join(words[1:])}))
                
        log.debug("First three modeled processes:\n%s" % 
                pformat(relMap.maps[:3]))
                
        return relMap

