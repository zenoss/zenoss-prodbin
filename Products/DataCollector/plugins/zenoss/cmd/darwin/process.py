##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """process
Maps ps output to process
"""

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class process(CommandPlugin):
    maptype = "OSProcessMap" 
    command = '/bin/ps axho command'
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    classname = "createFromObjectMap"


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting process information for device %s' % device.id)

        rm = self.relMap()
        for line in results.split("\n")[1:]:
            vals = line.split(None, 1)
            if len(vals) != 2: continue
            proc = dict(processText=line.strip())
            om = self.objectMap(proc)
            rm.append(om)
        return rm
