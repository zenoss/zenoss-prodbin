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


import Migrate


class SimpleDataPoint_list(Migrate.Step):

    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        dmd.buildMenus(dict(
            SimpleDataPoint_list=[dict(
                id='addDataPointsToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataPointsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0
            )]
        ))


SimpleDataPoint_list()
