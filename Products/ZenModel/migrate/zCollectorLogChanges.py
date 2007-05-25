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

__doc__='''

Add zCollectorLogChanges defaults

$Id:$
'''
import Migrate

class zCollectorLogChanges(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        
        # Set zCollectorLogChanges defaults
        if not dmd.Devices.hasProperty("zCollectorLogChanges"):
            dmd.Devices._setProperty("zCollectorLogChanges", 
										True, type="boolean")
        else:
            dmd.Devices.zCollectorLogChanges = True
        
zCollectorLogChanges()
