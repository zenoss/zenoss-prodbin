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

import string

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap
from sets import Set
import md5


class process(CommandPlugin):
    """
    maps ps output to process
    """
    maptype = "OSProcessMap" 
    command = 'ps axho comm,args'
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting process information for device %s' % device.id)

        rm = self.relMap()

        procs = Set()

        for line in results.split("\n"):
            vals = line.split()

            if len(vals) == 0:
                continue

            procName = vals[0]
            parameters = string.join(vals[1:], ' ')

            proc = {
                'procName' : procName,
                'parameters' : parameters
                }

            om = self.objectMap(proc)
            fullname = (om.procName + " " + om.parameters).rstrip()

            processes = device.getDmdRoot("Processes")
            for pc in processes.getSubOSProcessClassesGen():
                if pc.match(fullname):
                    om.setOSProcessClass = pc.getPrimaryDmdId()
                    id = om.procName
                    parameters = om.parameters.strip()
                    if parameters and not pc.ignoreParameters:
                        parameters = md5.md5(parameters).hexdigest()
                        id += ' ' + parameters
                    om.id = self.prepId(id)
                    if id not in procs:
                        procs.add(id)
                        rm.append(om)
                    break

        return rm
