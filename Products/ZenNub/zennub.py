#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Server that provides access to the Model databases."""

# std lib
import hashlib
import logging
import os
import sys
import time
import types

# 3rd party
from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks
from twisted.spread import pb
from twisted.cred import portal
from twisted.internet.endpoints import serverFromString

from zope.component import getUtility, adapts, provideUtility
from zope.event import notify
from zope.interface import implementer

# Prevent Products.ZenossStartup from loading all of the zenpacks.
# sys.modules['Products.ZenossStartup'] = types.ModuleType('Zenoss.ZenossStartup')

import Globals  # noqa: F401

from OFS.Application import import_products
import_products()
from Zope2.App.zcml import load_site
load_site()

from Products.ZenUtils.GlobalConfig import applyGlobalConfToParser
from Products.ZenUtils.Utils import zenPath, load_config
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenDaemon import ZenDaemon

from Products.ZenUtils.debugtools import ContinuousProfiler
from Products.ZenHub.server.utils import TCPDescriptor

# local
import Products.ZenHub as ZENHUB_MODULE
from Products.ZenHub.interfaces import (
    IHubConfProvider,
)
from Products.ZenHub.server import (
    config as server_config,
    getCredentialCheckers,
    IHubServerConfig,
    start_server,
)

from Products.ZenNub.services import (
    ModelerService,
    EventService,
    CommandPerformanceConfig,
    PythonConfig
)
from Products.ZenNub.db import get_nub_db
from Products.ZenNub.impact import update_all_impacts
from Products.ZenNub.cloudpublisher import CloudModelPublisher
from Products.ZenNub.yamlconfig import DEVICE_YAML

log = logging.getLogger('zen.zennub')


def _load_modules():
    # Due to the manipulation of sys.path during the loading of plugins,
    # we can get ObjectMap imported both as DataMaps.ObjectMap and the
    # full-path from Products.  The following gets the class registered
    # with the jelly serialization engine under both names:
    #  1st: get Products.DataCollector.plugins.DataMaps.ObjectMap
    from Products.DataCollector.plugins.DataMaps import ObjectMap  # noqa: F401
    #  2nd: get DataMaps.ObjectMap
    sys.path.insert(0, zenPath('Products', 'DataCollector', 'plugins'))
    import DataMaps  # noqa: F401


_load_modules()


class ZenNub(ZCmdBase):
    totalTime = 0.
    totalEvents = 0
    totalCallTime = 0.
    mname = name = 'zennub'
    devices_yaml_info = (None, None)

    def __init__(self, noopts=0, args=None, should_log=None):
        self.shutdown = False

        self.noopts = noopts
        self.inputArgs = args
        self.usage = "%prog [options]"
        self.parser = None
        self.buildParser()
        self.buildOptions()
        applyGlobalConfToParser(self.parser)
        self.parseOptions()
        if self.options.configfile:
            self.parser.defaults = self.getConfigFileDefaults(self.options.configfile)
            # We've updated the parser with defaults from configs, now we need
            # to reparse our command-line to get the correct overrides from
            # the command-line
            self.parseOptions()

        self.doesLogging = True
        self.setupLogging()

        if self.options.profiling:
            self.profiler = ContinuousProfiler('zenhub', log=self.log)
            self.profiler.start()

        # Load database
        log.info("Loading database")
        self.db = get_nub_db()
        self.db.load()

        # This technically shouldn't be necessary, because the impact
        # adapter would have been called whenever the applydatamap occurs.
        # So if it's time/resource consuming at all, we can likely remove it
        # from the startup.
        log.info("Updating all impacts")
        update_all_impacts()
        self.db.snapshot()

        self.db.set_model_publisher(CloudModelPublisher(
                self.options.zenossAddress,
                self.options.zenossApiKey,
                self.options.zenossHTTPS,
                self.options.zenossSource,
                self.options.modelBufferSize
        ))

        self._service_manager = ServiceManager()
        avatar = NubAvatar(self._service_manager)
        realm = NubRealm(avatar)
        authenticators = getCredentialCheckers(self.options.passwordfile)
        hubportal = portal.Portal(realm, authenticators)
        self._server_factory = pb.PBServerFactory(hubportal)

    def main(self):
        """Start the main event loop."""
        if self.options.cycle:
            reactor.callLater(0, self.heartbeat)
            reactor.addSystemEventTrigger(
                'before', 'shutdown', self._metric_manager.stop,
            )

        # Start ZenNub services server
        # Retrieve the server config object.
        config = getUtility(IHubServerConfig)

        # Build the network descriptor for the PerspectiveBroker server.
        pb_descriptor = TCPDescriptor.with_port(config.pbport)

        # Construct the PerspectiveBroker server
        pb_server = serverFromString(reactor, pb_descriptor)

        # Begin listening
        dfr = pb_server.listen(self._server_factory)

        # set the keep-alive config on the server's listening socket
        dfr.addCallback(lambda listener: setKeepAlive(listener.socket))
        log.info("Started server.")

        # watch the devices.xml file for changes (checking every few seconds)
        l = task.LoopingCall(self.checkDevicesXML)

        def err(reason):
            log.error("Error in checkDevicesXML LoopingCall: %s" % reason)
        l.start(10.0).addErrback(err)

        reactor.run()

        self.shutdown = True
        if self.options.profiling:
            self.profiler.stop()

    def checkDevicesXML(self):
        modified = False
        last_mtime, last_md5hash = self.devices_yaml_info

        mtime = os.stat(DEVICE_YAML).st_mtime
        if mtime != last_mtime:
            md5 = hashlib.md5()
            with open(DEVICE_YAML, 'rb') as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    md5.update(data)

            md5hash = md5.hexdigest()

            if md5hash != last_md5hash and last_md5hash is not None:
                modified = True

            self.devices_yaml_info = (mtime, md5hash)

        if modified:
            log.info("Change detected in %s.  Reloading.", DEVICE_YAML)
            self.db.reload_devices()

    def stop(self):
        self.shutdown = True

    def _getConf(self):
        confProvider = IHubConfProvider(self)
        return confProvider.getHubConf()

    def getService(self, service, monitor):
        return self._service_manager.getService(service, monitor)

    def buildOptions(self):
        """Add ZenNub command-line options."""
        ZenDaemon.buildOptions(self)
        self.parser.add_option(
            '--pbport', dest='pbport',
            type='int', default=server_config.defaults.pbport,
            help="Port to use for Twisted's pb service")
        self.parser.add_option(
            '--passwd', dest='passwordfile',
            type='string', default=zenPath('etc', 'hubpasswd'),
            help='File where passwords are stored')
        self.parser.add_option(
            '--monitor', dest='monitor',
            default='localhost',
            help='Name of the distributed monitor this hub runs on')
        self.parser.add_option(
            '--profiling', dest='profiling',
            action='store_true', default=False,
            help="Run with profiling on")

        self.parser.add_option('--zenoss-address',
                           dest='zenossAddress',
                           type='string',
                           default='api.zenoss.io:443',
                           help='Zenoss Cloud API URL, default: %default')

        self.parser.add_option('--zenoss-http',
                           dest='zenossHTTPS',
                           action="store_false",
                           default=True,
                           help='Use http rather than https for Zenoss Cloud API, default: %default')

        self.parser.add_option('--zenoss-api-key',
                           dest='zenossApiKey',
                           type='string',
                           default=None,
                           help='Zenoss Cloud API Key')

        self.parser.add_option('--zenoss-source',
                           dest='zenossSource',
                           type='string',
                           default=None,
                           help='Source tag data sent to Zenoss Cloud')

        self.parser.add_option('--modelBufferSize',
                               dest='modelBufferSize',
                               type='int',
                               default=4096,
                               help='Number of model updates to buffer if unable to contact the cloud')

    def parseOptions(self):
        # Override parseOptions to initialize and install the
        # ServiceManager configuration utility.
        super(ZenNub, self).parseOptions()
        server_config.pbport = int(self.options.pbport)
        config_util = server_config.ModuleObjectConfig(server_config)
        provideUtility(config_util, IHubServerConfig)

@implementer(portal.IRealm)
class NubRealm(object):
    """Defines realm from which avatars are retrieved.

    NOTE: Only one avatar is used.  Only one set of credentials are used to
    log into ZenHub, so the Realm cannot distingish between different clients.
    All connections look like the same user so they all get same avatar.
    """

    def __init__(self, avatar):
        """Initialize an instance of NubRealm.

        :param avatar: Represents the logged in client.
        :type avatar: HubAvatar
        """
        self.__avatar = avatar

    def requestAvatar(self, name, mind, *interfaces):
        """Return an avatar.

        Raises NotImplementedError if interfaces does not include
        pb.IPerspective.
        """
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        log.debug(
            "Client authenticated who=probably-%s",
            "zenhubworker" if mind else "collector-daemon",
        )
        return (
            pb.IPerspective,
            self.__avatar,
            lambda: self._disconnected(mind),
        )

    def _disconnected(self, mind):
        log.debug(
            "Client disconnected who=probably-%s",
            "zenhubworker" if mind else "collector-daemon",
        )


class NubAvatar(pb.Avatar):
    """Manages the connection between clients and ZenNub."""

    def __init__(self, services):
        """Initialize an instance of NubAvatar.

        :param services: The service manager
        :type services: ServiceManager
        """
        self.__services = services

    def perspective_ping(self):
        """Return 'pong'."""
        return 'pong'

    def perspective_getHubInstanceId(self):
        """Return the Control Center instance ID the running service."""
        return "Unknown"

    def perspective_getService(
            self, name, monitor=None, listener=None, options=None):
        """Return a reference to a ZenHub service.

        It also associates the service with a collector so that changes can be
        pushed back out to collectors.

        :param str name: The name of the service, e.g. "EventService"
        :param str monitor: The name of a collector, e.g. "localhost"
        :param listener: A remote reference to the client
        :type listener: twisted.spread.pb.RemoteReference
        :return: A reference to a service
        :rtype: .service.WorkerInterceptor
        """
        try:
            service = self.__services.getService(name, monitor)
        except RemoteBadMonitor:
            if log.isEnabledFor(logging.DEBUG):
                log.error("Monitor unknown monitor=%s", monitor)
            # This is a valid remote exception, so let it go through
            # to the collector daemon to handle
            raise
        except UnknownServiceError:
            log.error("Service not found service=%s", name)
            raise
        except Exception as ex:
            log.exception("Failed to load service service=%s", name)
            raise pb.Error(str(ex))
        else:
            if service is not None and listener:
                service.addListener(listener, options)
            return service

class ServiceManager(object):
    """Manages ZenHub service objects."""

    def __init__(self):
        """Initialize a ServiceManager instance.
        """
        self._services = {}
        self._services['EventService'] = EventService()
        self._services['ModelerService'] = ModelerService()
        self._services['Products.ZenHub.services.CommandPerformanceConfig'] = CommandPerformanceConfig()
        self._services['ZenPacks.zenoss.PythonCollector.services.PythonConfig'] = PythonConfig(self._services['ModelerService'])

    def getService(self, name, monitor):
        """Return (a Referenceable to) the named service."""

        # monitor name is disregarded as zennub is meant to be deployed
        # per-collector.

        if name not in self._services:
            raise UnknownServiceError(name)

        return self._services[name]



if __name__ == '__main__':
    ZenNub().main()
