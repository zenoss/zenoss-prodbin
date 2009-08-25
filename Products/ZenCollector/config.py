###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
The config module provides the implementation of the IConfigurationProxy
interface used within Zenoss Core. This implementation provides basic
configuration retrieval services directly from a remote ZenHub service.
"""

import zope.component
import zope.interface
import twisted.internet.defer

from Products.ZenCollector.interfaces import ICollector,\
                                             ICollectorPreferences,\
                                             IConfigurationProxy
from Products.ZenUtils.Utils import importClass

#
# creating a logging context for this module to use
#
import logging
log = logging.getLogger("zen.collector.config")


class ConfigurationProxy(object):
    """
    This implementation of IConfigurationProxy provides basic configuration
    retrieval from the remote ZenHub instance using the remote configuration
    service proxy as specified by the collector's configuration.
    """
    zope.interface.implements(IConfigurationProxy)

    def getPropertyItems(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        # Load any configuration properties for this daemon
        log.debug("Fetching daemon configuration properties")
        d = serviceProxy.callRemote('getConfigProperties')
        d.addCallback(lambda result: dict(result))
        return d

    def getThresholdClasses(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching threshold classes")
        d = serviceProxy.callRemote('getThresholdClasses')
        return d

    def getThresholds(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching collector thresholds")
        d = serviceProxy.callRemote('getCollectorThresholds')
        return d

    def getConfigProxies(self, prefs, ids=[]):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching configurations")
        d = serviceProxy.callRemote('getDeviceConfigs', ids)
        return d

    def deleteConfigProxy(self, prefs, id):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        # not implemented in the basic ConfigurationProxy
        return twisted.internet.defer.succeed(None)

    def updateConfigProxy(self, prefs, config):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        # not implemented in the basic ConfigurationProxy
        return twisted.internet.defer.succeed(None)
