
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

        
