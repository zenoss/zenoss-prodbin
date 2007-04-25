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
'Add/subtract monitors'

import Migrate

class Monitors(Migrate.Step):
    "Set the sub_class value on the usual Monitor objects"
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        dmd.Monitors.sub_class = 'MonitorClass'
        dmd.Monitors.Performance.sub_class = 'PerformanceConf'
        dmd.Monitors.StatusMonitors.sub_class = 'StatusMonitorConf'

Monitors()


