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
from Products.Zuul.interfaces import IPowerSupplyInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class PowerSupplyInfo(ComponentInfo):
    implements(IPowerSupplyInfo)

    watts = ProxyProperty('watts')
    type = ProxyProperty('type')
    state = ProxyProperty('state')

    @property
    def millivolts(self):
        return self._object.millivolts()
