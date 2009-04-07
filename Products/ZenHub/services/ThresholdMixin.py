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

from Products.ZenHub.PBDaemon import translateError

class ThresholdMixin:
    _cached_thresholdClasses = []

    @translateError
    def remote_getThresholdClasses(self):
        if not self._cached_thresholdClasses:
            from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
            classes = [MinMaxThreshold]
            for pack in self.dmd.ZenPackManager.packs():
                classes += pack.getThresholdClasses()
            self._cached_thresholdClasses = map(lambda c: c.__module__, classes)
        return self._cached_thresholdClasses


    @translateError
    def remote_getCollectorThresholds(self):
        from Products.ZenModel.BuiltInDS import BuiltInDS
        return self.config.getThresholdInstances(BuiltInDS.sourcetype)

        
