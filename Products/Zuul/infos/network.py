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

import re
from zope.interface import implements
from Products.Zuul.interfaces import IIpNetworkInfo, IIpAddressInfo
from Products.Zuul.infos import InfoBase
from Products.Zuul.decorators import info
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo

class IpNetworkInfo(InfoBase):
    implements(IIpNetworkInfo)

    @property
    def name(self):
        return self._object.getNetworkName()

    @property
    def ipcount(self):
        return str(self._object.countIpAddresses()) + '/' + \
               str(self._object.freeIps())

    # zProperties
    def getZAutoDiscover(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAutoDiscover', True, translate)

    def setZAutoDiscover(self, data):
        setZPropertyInfo(self._object, 'zAutoDiscover', **data)

    zAutoDiscover = property(getZAutoDiscover, setZAutoDiscover)

    def getZDrawMapLinks(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zDrawMapLinks', True, translate)

    def setZDrawMapLinks(self, data):
        setZPropertyInfo(self._object, 'zDrawMapLinks', **data)

    zDrawMapLinks = property(getZDrawMapLinks, setZDrawMapLinks)
    
    def getZDefaultNetworkTree(self):
        def translate(rawValue):
            return ', '.join( [str(x) for x in rawValue] )
        return getZPropertyInfo(self._object, 'zDefaultNetworkTree', 
                                translate=translate, translateLocal=True)

    _decimalDigits = re.compile('\d+')

    def setZDefaultNetworkTree(self, data):
        
        # convert data['localValue'] (string with comma and whitespace
        # delimeters) to tuple of integers
        digits = self._decimalDigits.findall( data['localValue'] )
        data['localValue'] = tuple( int(x) for x in digits )
        
        setZPropertyInfo(self._object, 'zDefaultNetworkTree', **data)

    zDefaultNetworkTree = property(getZDefaultNetworkTree, setZDefaultNetworkTree)

    def getZPingFailThresh(self):
        return getZPropertyInfo(self._object, 'zPingFailThresh')

    def setZPingFailThresh(self, data):
        setZPropertyInfo(self._object, 'zPingFailThresh', **data)

    zPingFailThresh = property(getZPingFailThresh, setZPingFailThresh)

    def getZIcon(self):
        return getZPropertyInfo(self._object, 'zIcon')

    def setZIcon(self, data):
        setZPropertyInfo(self._object, 'zIcon', **data)

    zIcon = property(getZIcon, setZIcon)

    def getZSnmpStrictDiscovery(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zSnmpStrictDiscovery', True, translate)

    def setZSnmpStrictDiscovery(self, data):
        setZPropertyInfo(self._object, 'zSnmpStrictDiscovery', **data)

    zSnmpStrictDiscovery = property(getZSnmpStrictDiscovery, setZSnmpStrictDiscovery)

    def getZPreferSnmpNaming(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zPreferSnmpNaming', True, translate)

    def setZPreferSnmpNaming(self, data):
        setZPropertyInfo(self._object, 'zPreferSnmpNaming', **data)

    zPreferSnmpNaming = property(getZPreferSnmpNaming, setZPreferSnmpNaming)

class IpAddressInfo(InfoBase):
    implements(IIpAddressInfo)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def pingstatus(self):
        if not self._object.interface():
            return 5
        return self._object.getPingStatus()

    @property
    def snmpstatus(self):
        if not self._object.interface():
            return 5
        return self._object.getSnmpStatus()
