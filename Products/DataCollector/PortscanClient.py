###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """PortscanClient
Performance collector of port-scanning
"""

import logging

from twisted.internet import reactor
from twisted.python import failure

import Globals

from Products.ZenUtils import PortScan

log = logging.getLogger("zen.PortscanClient")

from BaseClient import BaseClient

class PortscanClient(BaseClient):
    """
    Implement the DataCollector Client interface for port-scanning
    """

    def __init__(self, hostname, ipaddr, options=None, device=None, 
                 datacollector=None, plugins=[]):
        """
        Initializer

        @param hostname: name of the remote device
        @type hostname: string
        @param ipaddr: IP address of the remote device
        @type ipaddr: string
        @param options: optparse options
        @type options: optparse options object
        @param device: DMD device object
        @type device: device object
        @param datacollector: performance data collector object
        @type datacollector: datacollector object
        @param plugins: performance data collector plugin
        @type plugins: list of plugin objects
        """
        BaseClient.__init__(self, device, datacollector)
        self.hostname = hostname
        self.options = options
        self.plugins = plugins
        self.results = []

        maxPort = getattr(device,'zIpServiceMapMaxPort', 1024)
        self.portRange = (1, maxPort)

        #self.portList = getattr(device,'zPortscanPortList', [])
        self.portList = []

        if self.portList:
            kwds = {'portList': self.portList}
        else:
            kwds = {'portRange': self.portRange}
        kwds.update(dict(timeout=self.options.portscantimeout))
        self.scanner = PortScan.Scanner(ipaddr, **kwds)
        

    def run(self):
        """
        Start portscan collection.
        """
        for plugin in self.plugins:
            log.debug("Sending queries for plugin %s", plugin.name())
            d = self.scanner.prepare()
            d.addCallback(self._cbScanComplete, plugin)
            d.addErrback(self._ebScanError, plugin)


    def _cbScanComplete(self, unused, plugin):
        """
        Start portscan collection.

        @param unused: unused (unused)
        @type unused: object
        @param plugin: performance data collector plugin
        @type plugin: plugin object
        """
        log.debug("Received plugin:%s getOids", plugin.name())
        self.clientFinished(plugin)


    def _ebScanError( self, err, plugin):
        """
        Handle an error generated by one of our requests.

        @param err: result from the collection run
        @type err: result or Exception
        @param plugin: performance data collector plugin
        @type plugin: plugin object
        """
        self.clientFinished(plugin)
        log.debug('Device %s plugin %s %s', self.hostname, plugin.name(), err)
        if isinstance(err, failure.Failure):
            trace = err.getTraceback()
        else:
            trace = log.getException(err)
        log.error(
            """Device %s plugin %s received an unexpected error: %s""",
            self.hostname, plugin.name(), trace,
        )


    def getResults(self):
        """
        ZenUtils.PortScan records open ports in a list that are the
        values for a key in a dict where the key is the IP address
        scanned.

        For example, if we scan host 10.0.4.55 and ports 22 and 80 are
        open, getSuccesses() will return the following:

            {'10.0.4.55': [22, 80]}

        @return: results
        @rtype: list of strings
        """
        return self.results


    def clientFinished(self, plugin):
        """
        Tell the datacollector that we are all done.

        @param plugin: performance data collector plugin
        @type plugin: plugin object
        """
        log.info("portscan client finished collection for %s" % self.hostname)
        # ApplyDataMap.processClient() expect an iterable with two
        # elements: the plugin name and the results, so we set this
        # here.        
        self.results.append((plugin, self.scanner.getSuccesses()))
        if self.datacollector:
            self.datacollector.clientFinished(self)
        else:
            reactor.stop()


def buildOptions(parser=None, usage=None):
    """
    Create the command-line options list
    """
   
    if not usage:
        usage = "%prog [options] hostname[:port] oids"

    if not parser:
        from optparse import OptionParser
        parser = OptionParser(usage=usage)
    # XXX this function may need options later, so we'll keep this here
    # as a reminder for now
    #parser.add_option('--snmpCommunity',
    #            dest='snmpCommunity',
    #            default=defaultSnmpCommunity,
    #            help='Snmp Community string')


if __name__ == "__main__":
    import sys
    sys.path.extend([
        '/usr/local/zenoss/Products/DataCollector/plugins',
    ])
    import pprint
    from zenoss.portscan import IpServiceMap

    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(20)
    ipmap = IpServiceMap.IpServiceMap()
    psc = PortscanClient("localhost", '127.0.0.1', plugins=[ipmap,])
    psc.run()
    reactor.run()
    pprint.pprint(psc.getResults())
