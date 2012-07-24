##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IOSProcessInfo
from Products.Zuul.infos.component import ComponentInfo, ServiceMonitor

class OSProcessInfo(ComponentInfo):
    implements(IOSProcessInfo)

    @property
    @info
    def processClass(self):
        return self._object.osProcessClass()

    @property
    def processName(self):
        return self._object.name()

    @property
    def description(self):
        return self._object.osProcessClass().description

    def getAlertOnRestart(self):
        return self._object.alertOnRestart()
    def setAlertOnRestart(self, value):
        if value is not None:
            self._object.zAlertOnRestart = value
        else:
            self._object.deleteZenProperty('zAlertOnRestart')
    alertOnRestart = property(getAlertOnRestart, setAlertOnRestart)

    def getFailSeverity(self):
        return self._object.getFailSeverity()
    def setFailSeverity(self, value):
        if value is not None:
            self._object.zFailSeverity = value
        else:
            self._object.deleteZenProperty('zFailSeverity')
    failSeverity = property(getFailSeverity, setFailSeverity)

    monitor = ServiceMonitor()

    @property
    def monitored(self):
        return self._object.monitored()
