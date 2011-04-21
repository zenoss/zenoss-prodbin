###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from Products.Zuul.interfaces import IExpansionCardInfo
from Products.Zuul.decorators import info
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class ExpansionCardInfo(ComponentInfo):
    implements(IExpansionCardInfo)

    slot = ProxyProperty('slot')
    serialNumber = ProxyProperty('serialNumber')
    socket = ProxyProperty('socket')
    clockspeed = ProxyProperty('clockspeed')
    extspeed = ProxyProperty('extspeed')
    voltage = ProxyProperty('voltage')
    cacheSizeL1 = ProxyProperty('cacheSizeL1')
    cacheSizeL2 = ProxyProperty('cacheSizeL2')

    @property
    @info
    def manufacturer(self):
        pc = self._object.productClass()
        if (pc):
            return pc.manufacturer()

    @property
    @info
    def product(self):
        return self._object.productClass()

    @property
    def usesMonitorAttribute(self):
        return False

    monitor = False

    @property
    def monitored(self):
        return ""
