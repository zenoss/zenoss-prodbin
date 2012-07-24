##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IFanInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class FanInfo(ComponentInfo):
    implements(IFanInfo)

    state = ProxyProperty('state')
    type = ProxyProperty('type')

    @property
    def rpm(self):
        return self._object.rpm()
