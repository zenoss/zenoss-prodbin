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

class ThresholdMixin:

    def remote_getThresholdClasses(self):
        from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
        classes = [MinMaxThreshold]
        for pack in self.dmd.packs():
            classes += pack.getThresholdClasses()
        return map(lambda c: c.__module__, classes)


    def remote_getCollectorThresholds(self):
        from Products.ZenModel.BuiltInDS import BuiltInDS
        return self.config.getThresholdInstances(BuiltInDS.sourcetype)

        
