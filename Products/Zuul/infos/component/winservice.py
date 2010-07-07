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
from Products.Zuul.utils import safe_hasattr

class WinServiceInfo(ComponentInfo):
    implements(IWinServiceInfo)

    def __init__(self, *args, **kwargs):
        super(ComponentInfo, self).__init__(*args, **kwargs)
        self.serviceClassUid = self._object.serviceclass().getPrimaryUrlPath()

    @property
    @info
    def serviceClass(self):
        return self._object.serviceclass()

    @property
    def usesMonitorAttribute(self):
        return ( self._object.getAqProperty("zMonitor")
               and ( not safe_hasattr(self._object, "startMode")
                     or self._object.startMode != "Disabled" ))

    @property
    def monitored(self):
        return self._object.monitored() if self.usesMonitorAttribute else ""

    @property
    def caption(self):
        return self._object.caption()

    command = ProxyProperty('id')

    def getFailSeverity(self):
        return self._object.getFailSeverity()
    def setFailSeverity(self, value):
        if value is not None:
            self._object.zFailSeverity = value
        else:
            self._object.deleteZenProperty('zFailSeverity')
    failSeverity = property(getFailSeverity, setFailSeverity)

    def status(self):
        return self._object.getStatus()

    serviceName = ProxyProperty('serviceName')
    caption = ProxyProperty('caption')
    serviceType = ProxyProperty('serviceType')
    startMode = ProxyProperty('startMode')
    startName = ProxyProperty('startName')
    pathName = ProxyProperty('pathName')

