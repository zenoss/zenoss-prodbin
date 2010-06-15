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
from Products.Zuul.interfaces import IIpRouteEntryInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo

class IpRouteEntryInfo(ComponentInfo):
    implements(IIpRouteEntryInfo)

    @property
    @info
    def destination(self):
        target = self._object.target()
        return target if target else self._object._target

    @property
    @info
    def nextHop(self):
        ip = self._object.nexthop()
        return ip if ip else self._object._nexthop

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def usesMonitorAttribute(self):
        return False

    monitor = False

    @property
    def monitored(self):
        return ""

    protocol = ProxyProperty('routeproto')
    type = ProxyProperty('routetype')

