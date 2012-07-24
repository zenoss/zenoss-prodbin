##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenHub.PBDaemon import translateError

class ThresholdMixin:
    _cached_thresholdClasses = []

    @translateError
    def remote_getThresholdClasses(self):
        if not self._cached_thresholdClasses:
            from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
            from Products.ZenModel.ValueChangeThreshold import ValueChangeThreshold
            classes = [MinMaxThreshold, ValueChangeThreshold]
            for pack in self.dmd.ZenPackManager.packs():
                classes += pack.getThresholdClasses()
            self._cached_thresholdClasses = map(lambda c: c.__module__, classes)
        return self._cached_thresholdClasses


    @translateError
    def remote_getCollectorThresholds(self):
        from Products.ZenModel.BuiltInDS import BuiltInDS
        return self.config.getThresholdInstances(BuiltInDS.sourcetype)
