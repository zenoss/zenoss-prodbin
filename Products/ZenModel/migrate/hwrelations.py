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
'''
import Migrate

class DeviceHWRelations(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import twotwoindexing
        self.dependencies = [ twotwoindexing.twotwoindexing ]

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.hw.buildRelations()

DeviceHWRelations()
