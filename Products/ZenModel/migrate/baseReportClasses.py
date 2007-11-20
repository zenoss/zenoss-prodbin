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
from Products.ZenModel.DeviceReportClass import DeviceReportClass
from Products.ZenModel.CustomDeviceReportClass import CustomDeviceReportClass
from Products.ZenModel.GraphReportClass import GraphReportClass

# graphReports is using buildMenus so we let it go first before we modify
# some of the same menus.

class BaseReportClasses(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        def BuildOrSwitchReportClass(rcId, reportClass):        
            rc = getattr(dmd.Reports, rcId, None)
            if rc:
                if not isinstance(rc, reportClass):
                    rc.__class__ = reportClass
            else:
                rc = reportClass(rcId)
                dmd.Reports._setObject(rc.id, rc)
            return rc
        
        BuildOrSwitchReportClass('Device Reports', DeviceReportClass)
        BuildOrSwitchReportClass('Custom Device Reports', CustomDeviceReportClass)
        BuildOrSwitchReportClass('Graph Reports', GraphReportClass)
        
        # Menus

        reportList = getattr(dmd.zenMenus, 'Report_list')
        reportList.zenMenuItems.addDeviceReport.allowed_classes = ['CustomDeviceReportClass']
        reportList.zenMenuItems.deleteDeviceReports.allowed_classes = [
            'CustomDeviceReportClass', 'GraphReportClass', 'MultiGraphReportClass']


BaseReportClasses()
