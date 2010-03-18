###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IOSProcessInfo
from Products.Zuul.infos.component import ComponentInfo

class OSProcessInfo(ComponentInfo):
    implements(IOSProcessInfo)

    @property
    @info
    def processClass(self):
        return self._object.osProcessClass()

    @property
    def processName(self):
        return self._object.name()

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

