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

Add a default zFileSystemMapIgnoreTypes property to key device classes now that
the HRFileSystemMap uses it.

'''
import Migrate

class addDefaultZFileSystemMapIgnoreTypes(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        if not dmd.Devices.zFileSystemMapIgnoreTypes:
            dmd.Devices.zFileSystemMapIgnoreTypes = [
                'other', 'ram', 'virtualMemory', 'removableDisk', 'floppyDisk',
                'compactDisk', 'ramDisk', 'flashMemory', 'networkDisk']

        try:
            if not dmd.Devices.Server.Windows.WMI.hasProperty(
                'zFileSystemMapIgnoreTypes'):
                dmd.Devices.Server.Windows.WMI._setProperty(
                    'zFileSystemMapIgnoreTypes', [])
        except AttributeError:
            pass

addDefaultZFileSystemMapIgnoreTypes()

