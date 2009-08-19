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

    def configure(self, prefs, configs=[]):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        self._prefs = prefs
        return self._getRemoteConfig(configs)

    def deleteConfig(self, prefs, configId):
        # not implemented in the basic ConfigurationProxy
        pass

    def updateConfig(self, prefs, config):
        # not implemented in the basic ConfigurationProxy
        pass

    def _getRemoteConfig(self, configs):
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        # Load any configuration properties for this daemon
        log.debug("Fetching daemon configuration properties")
        d = serviceProxy.callRemote('getConfigProperties')
        d.addCallback(self._handlePropertyItems, configs, serviceProxy)
        return d

    def _handlePropertyItems(self, result, configs, serviceProxy):
        table = dict(result)

        for name, value in table.iteritems():
            if not hasattr(self._prefs, name):
                log.debug("ICollectorPreferences does not have attribute %s",
                          name)
            elif getattr(self._prefs, name) != value:
                log.debug("Updated %s config to %s", name, value)
                setattr(self._prefs, name, value)

        # retrieve the default RRD command and convert it from a list of strings
        # to a single string with newline separators
        defaultRRDCreateCommand = table.get('defaultRRDCreateCommand', None)
        defaultRRDCreateCommand = '\n'.join(defaultRRDCreateCommand)

        # Find out what Python Class objects are required for thresholds
        log.debug("Fetching threshold classes")
        d = serviceProxy.callRemote('getThresholdClasses')
        d.addCallback(self._handleThresholdClasses,
                      configs, 
                      serviceProxy, 
                      defaultRRDCreateCommand)
        return d

    def _handleThresholdClasses(self,
                                result,
                                configs,
                                serviceProxy,
                                rrdCreateCommand):
        classes = result
        log.debug("Loading classes %s", classes)
        for c in classes:
            try:
                importClass(c)
            except ImportError:
                log.exception("Unable to import class %s", c)

        # Find all the actual collector thresholds needed
        log.debug("Fetching collector thresholds")
        d = serviceProxy.callRemote('getCollectorThresholds')
        d.addCallback(self._handleCollectorThresholds,
                      configs,
                      serviceProxy,
                      rrdCreateCommand)
        return d

    def _handleCollectorThresholds(self, 
                                   result, 
                                   configs, 
                                   serviceProxy, 
                                   rrdCreateCommand):
        log.debug("_handleCollectorThresholds: result=%s", result)

        # inform the collector of i
        self._collector.configureRRD(rrdCreateCommand, result)

        # Fetch the configuration for this collector
        log.debug("Fetching configurations")
        d = serviceProxy.callRemote('getDeviceConfigs', configs)
        d.addCallback(self._handleConfigs, serviceProxy)
        return d

    def _handleConfigs(self, result, serviceProxy):
        log.debug("_handleConfigs: result=%s", result)
        return result
