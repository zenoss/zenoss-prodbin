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


class AddToGraphMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    

    def cutover(self, dmd):
        
        dsMenu = dmd.zenMenus._getOb('DataSource_list', None)
        if dsMenu and not dsMenu.zenMenuItems._getOb('addDataSourcesToGraphs', None):
            dsMenu.manage_addZenMenuItem(
                id='addDataSourcesToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataSourcesToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)

        dpMenu = dmd.zenMenus._getOb('DataPoint_list', None)
        if dpMenu and not dpMenu.zenMenuItems._getOb('addDataPointsToGraphs', None):
            dpMenu.manage_addZenMenuItem(
                id='addDataPointsToGraphs',
                description='Add to Graphs...',
                action='dialog_addDataPointsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)

        threshMenu = dmd.zenMenus._getOb('Threshold_list', None)
        if threshMenu and not threshMenu.zenMenuItems._getOb('addThresholdsToGraphs', None):
            threshMenu.manage_addZenMenuItem(
                id='addThresholdsToGraphs',
                description='Add to Graphs...',
                action='dialog_addThresholdsToGraphs',
                isdialog=True,
                permissions=('Change Device',),
                ordering=80.0)


AddToGraphMenuItem()
