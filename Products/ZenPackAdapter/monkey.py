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

import time
import os.path

from Products.ZenUtils.Utils import monkeypatch
from Products.ZenHub.PBDaemon import PBDaemon
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenPackAdapter.cloudpublisher import CloudMetricPublisher


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
