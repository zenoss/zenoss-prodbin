###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Add zInterfaceMapIgnoreDescriptions zProperty.  This allows interfaces to be
ignored when modeled if their description matches this regex.
'''
import Migrate


class addzInterfaceMapIgnoreDescriptions(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Devices, 'zInterfaceMapIgnoreDescriptions' ):
            dmd.Devices._setProperty('zInterfaceMapIgnoreDescriptions', '', 'string')

addzInterfaceMapIgnoreDescriptions()
