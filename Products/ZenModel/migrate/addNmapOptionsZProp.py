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
__doc__='''

Add a zProperty to allow for control of the nmap portscan plugin.

'''
import Migrate

class addNmapOptionsZProp(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        if not hasattr(dmd.Devices, 'zNmapPortscanOptions'):
            dmd.Devices._setProperty("zNmapPortscanOptions", "-p 1-1024;-sT;--open;-oG -")

addNmapOptionsZProp()

