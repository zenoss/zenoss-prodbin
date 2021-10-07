##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# TEMPORARY monkeypatches to other parts of the platform.  These need to be
# integrated properly, but for the purposes of this POC, i wanted to keep them
# isolated.
#
# This file is loaded by Products.ZenUtils (__init__.py)

import socket
import sys
import time
import os.path
import logging
from twisted.internet import reactor, defer

from Products.ZenUtils.Utils import monkeypatch
from Products.ZenHub.PBDaemon import PBDaemon
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenPackAdapter.cloudpublisher import CloudMetricPublisher

import zenwrapt
zenwrapt.initialize()
LOG = logging.getLogger("zen.monkeypatches")

@monkeypatch(PBDaemon)
def publisher(self):
    if not self._publisher:
        self._publisher = CloudMetricPublisher(
            self.options.zenossAddress,
            self.options.zenossApiKey,
            self.options.zenossHTTPS,
            self.options.zenossSource,
            self.options.metricBufferSize
        )
    return self._publisher

@monkeypatch(PBDaemon)
def buildOptions(self):
    original(self)
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

    self.parser.add_option('--collector-type',
                       dest='zpaCollectorType',
                       type='string',
                       default=os.path.basename(sys.argv[0]),
                       help='Type of collector process (process name, generally)')

    self.parser.add_option('--collector-instance-id',
                       dest='zpaCollectorId',
                       type='string',
                       default=socket.gethostname(),
                       help='Unique Identifier for this collector process/container')
@monkeypatch(CmdBase)
def parseOptions(self):
    from Products.ZenPackAdapter.yamlconfig import load_config_yaml, CONFIG_YAML
    while not os.path.exists(CONFIG_YAML):
        print "  waiting for %s" % CONFIG_YAML
        time.sleep(3)

    config = load_config_yaml()

    option_type = {}
    for opt in self.parser.option_list:
        if opt.dest and opt.type:
                option_type[opt.dest] = opt.type

    for k, v in config.iteritems():
        if k in option_type:
            self.parser.defaults[k] = str(v)
        else:
            print "WARNING: While parsing %s, \"%s\" is not a valid option (ignoring)" % (CONFIG_YAML, k)

    original(self)


# push events every 5 seconds.
@monkeypatch(PBDaemon)
def pushEventsLoop(self):

    @defer.inlineCallbacks
    def zpa_EventLoop(pbDaemon):
        if pbDaemon and getattr(pbDaemon, 'pushEvents', None):
            try:
                yield pbDaemon.pushEvents()
            except Exception as e:
                LOG.error("Error pushing events: %s.", e)
        reactor.callLater(5, zpa_EventLoop, pbDaemon)

    try:
        if not reactor.running:
            LOG.critical("Reactor not running. Event Loop Disabled")
            return
        reactor.callLater(0, zpa_EventLoop, self)
    except Exception as outer:
        LOG.error("Error calling zpa event loop: %s", outer)

