###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import socket
import logging
log = logging.getLogger("zen.SnmpClient")

from twisted.internet import reactor, error, defer
from twisted.python import failure
try:
    from pynetsnmp.twistedsnmp import snmpprotocol, AgentProxy
except ImportError:
    from twistedsnmp import snmpprotocol
    from twistedsnmp.agentproxy import AgentProxy

import Globals

from Products.ZenUtils.IpUtil import isip
from Products.ZenUtils.Driver import drive

global defaultTries, defaultTimeout
defaultTries = 2
defaultTimeout = 1

DEFAULT_MAX_OIDS_BACK = 40

class SnmpClient(object):

    def __init__(self, hostname, ipaddr, options=None, device=None, 
                 datacollector=None, plugins=[]):
        global defaultTries, defaultTimeout
        self.hostname = hostname
        self.device = device
        self.options = options
        self.datacollector = datacollector
        self.plugins = plugins

        self._getdata = {}
        self._tabledata = {}

        community = getattr(device, 'zSnmpCommunity', "public")
        port = int(getattr(device, 'zSnmpPort', 161))
        snmpver = getattr(device, 'zSnmpVer', "v1")
        self.tries = int(getattr(device,'zSnmpTries', defaultTries))
        self.timeout = float(getattr(device,'zSnmpTimeout', defaultTimeout))

        srcport = snmpprotocol.port()
        self.proxy = AgentProxy(ipaddr, port, community, snmpver,
                                protocol=srcport.protocol)
        if not hasattr(self.proxy, 'open'):
            def doNothing(): pass
            self.proxy.open = doNothing
            self.proxy.close = doNothing


    def run(self):
        """Start snmp collection.
        """
        log.debug("timeout=%s, tries=%s", self.timeout, self.tries)
        self.proxy.open()
        drive(self.doRun).addBoth(self.clientFinished)


    def checkCiscoChange(self, driver):
        """Check to see if a cisco box has changed.
        """
        device = self.device
        yield self.proxy.get(['.1.3.6.1.4.1.9.9.43.1.1.1.0'],
                             timeout=self.timeout,
                             retryCount=self.tries)
        lastpolluptime = device.getLastPollSnmpUpTime()
        log.debug("lastpolluptime = %s", lastpolluptime)
        try:
            lastchange = driver.next().values()[0]
            log.debug("lastchange = %s", lastchange)
            if lastchange == lastpolluptime: 
                log.info("skipping cisco device %s no change detected",
                         device.id)
                yield defer.succeed(False)
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except Exception:
            pass
        yield defer.succeed(False)


    def doRun(self, driver):
        # test snmp connectivity
        log.debug("Testing SNMP configuration")
        yield self.proxy.walk('.1', timeout=self.timeout, retryCount=self.tries)
        try:
            driver.next()
        except Exception, ex:
            log.error("Unable to talk to device %s on %s:%s using community '%s'",
                      self.device.id,
                      self.proxy.ip,
                      self.proxy.port or 161,
                      self.proxy.community)
            return

        changed = True
        if not self.options.force and self.device.snmpOid.startswith(".1.3.6.1.4.1.9"):
            yield drive(self.checkCiscoChange)
            changed = driver.next()
        if changed:
            yield drive(self.collect)


    def collect(self, driver):
        for plugin in self.plugins:
            try:
                log.debug('running %s', plugin)
                pname = plugin.name()
                self._tabledata[pname] = {}
                log.debug("sending queries for plugin %s", pname)
                if plugin.snmpGetMap:
                    yield self.proxy.get(plugin.snmpGetMap.getoids(),
                                       timeout=self.timeout,
                                       retryCount=self.tries)
                    self._getdata[pname] = driver.next()
                for tmap in plugin.snmpGetTableMaps:
                    rowSize = len(tmap.getoids())
                    maxRepetitions = max(DEFAULT_MAX_OIDS_BACK / rowSize, 1)
                    yield self.proxy.getTable(tmap.getoids(),
                                              timeout=self.timeout,
                                              retryCount=self.tries,
                                              maxRepetitions=maxRepetitions)
                    self._tabledata[pname][tmap] = driver.next()
            except Exception, ex:
                if not isinstance( ex, error.TimeoutError ):
                    log.exception("device %s plugin %s unexpected error",
                                  self.hostname, pname)


    def getResults(self):
        """Return data for this client in the form
        ((pname, (getdata, tabledata),)
        getdata = {'.1.2.4.5':"value",}
        tabledata = {tableMap : {'.1.2.3.4' : {'.1.2.3.4.1': "value",...}}} 
        """
        data = []
        for plugin in self.plugins:
            pname = plugin.name()
            getdata = self._getdata.get(pname,{})
            tabledata = self._tabledata.get(pname,{})
            if getdata or tabledata:
                data.append((pname, (getdata, tabledata)))
        return data 

    def clientFinished(self, result):
        log.info("snmp client finished collection for %s" % self.hostname)
        if isinstance(result, failure.Failure):
            from twisted.internet import error
            if isinstance(result.value, error.TimeoutError):
                log.error("Device %s timed out: are "
                          "your SNMP settings correct?", self.hostname)
            else:
                log.error("Device %s had an error: %s", self.hostname, result)
        self.proxy.close()
        """tell the datacollector that we are all done"""
        if self.datacollector:
            self.datacollector.clientFinished(self)
        else:
            reactor.stop()



def buildOptions(parser=None, usage=None):
    "build options list that both telnet and ssh use"
   
    if not usage:
        usage = "%prog [options] hostname[:port] oids"

    if not parser:
        from optparse import OptionParser
        parser = OptionParser(usage=usage, 
                                   version="%prog " + __version__)
  
    parser.add_option('--snmpCommunity',
                dest='snmpCommunity',
                default=defaultSnmpCommunity,
                help='Snmp Community string')


if __name__ == "__main__":
    import pprint
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(20)
    import sys
    sys.path.append("plugins")
    from plugins.zenoss.snmp.InterfaceMap import InterfaceMap
    ifmap = InterfaceMap()
    sc = SnmpClient("gate.confmon.loc", community="zentinel", plugins=[ifmap,])
    reactor.run()
    pprint.pprint(sc.getResults())
