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
from Products.Zuul.interfaces import IWinServiceInfo
from Products.Zuul.infos.component import ComponentInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.decorators import info

class WinServiceInfo(ComponentInfo):
    implements(IWinServiceInfo)

    @property
    @info
    def serviceClass(self):
        return self._object.serviceClass()

    command = ProxyProperty('id')

    def getFailSeverity(self):
        return self._object.getFailSeverity()
    def setFailSeverity(self, value):
        if value is not None:
            self._object.zFailSeverity = value
        else:
            self._object.deleteZenProperty('zFailSeverity')
    failSeverity = property(getFailSeverity, setFailSeverity)

    serviceType = ProxyProperty('serviceType')
    startMode = ProxyProperty('startMode')
    startName = ProxyProperty('startName')
    acceptPause = ProxyProperty('acceptPause')
    acceptStop = ProxyProperty('acceptStop')
    pathName = ProxyProperty('pathName')

