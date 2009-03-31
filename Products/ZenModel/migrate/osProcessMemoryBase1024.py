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
import Migrate

class OSProcessMemoryBase1024(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        try:
            g = dmd.Devices.rrdTemplates.OSProcess.graphDefs.Memory
            g.base = True
        except AttributeError:
            # We don't care of the OSProcess tempalte doesn't exist. We also
            # don't care if the Memory graph doesn't exist.
            pass

osProcessMemoryBase1024 = OSProcessMemoryBase1024()