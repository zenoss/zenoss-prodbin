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
from Products.Zuul.interfaces import IIpServiceInfo
from Products.Zuul.infos.component import ComponentInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.decorators import info
from zope.schema.vocabulary import SimpleVocabulary

def serviceIpAddressesVocabulary(context):
    return SimpleVocabulary.fromValues(context.ipaddresses)

class IpServiceInfo(ComponentInfo):
    implements(IIpServiceInfo)

    @property
    @info
    def serviceClass(self):
        return self._object.serviceClass()

    def getManageIp(self):
        return self._object.getManageIp()
    def setManageIp(self, value):
        self._object.manageIp = value
    manageIp = property(getManageIp, setManageIp)

    port = ProxyProperty('port')
    ipaddresses = ProxyProperty('ipaddresses')
    protocol = ProxyProperty('protocol')
    discoveryAgent = ProxyProperty('discoveryAgent')

    def getSendString(self):
        return self._object.getSendString()
    def setSendString(self, value):
        self._object.setAqProperty("sendString", value, "string")
    sendString = property(getSendString, setSendString)

    def getExpectRegex(self):
        return self._object.getExpectRegex()
    def setExpectRegex(self, value):
        self._object.setAqProperty("expectRegex", value, "string")
    expectRegex = property(getExpectRegex, setExpectRegex)

