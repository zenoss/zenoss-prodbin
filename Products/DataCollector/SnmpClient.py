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

from pynetsnmp.twistedsnmp import snmpprotocol, AgentProxy

import Globals

from Products.ZenUtils.IpUtil import isip
from Products.ZenUtils.Driver import drive

global defaultTries, defaultTimeout
defaultTries = 2
defaultTimeout = 1
defaultSnmpCommunity = 'public'

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

        from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
        self.connInfo = SnmpConnInfo(device)
        srcport = snmpprotocol.port()
        self.proxy = self.connInfo.createSession(srcport.protocol)


    def run(self):
        """Start snmp collection.
        """
        log.debug("Starting %s", self.connInfo.summary())
        self.proxy.open()
        drive(self.doRun).addBoth(self.clientFinished)


    def checkCiscoChange(self, driver):
        """Check to see if a cisco box has changed.
        """
        device = self.device
        yield self.proxy.get(['.1.3.6.1.4.1.9.9.43.1.1.1.0'])
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
        yield self.proxy.walk('.1')
        try:
            driver.next()
        except Exception, ex:
            log.exception("Unable to talk: ", self.connInfo.summary())
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
                    yield self.proxy.get(plugin.snmpGetMap.getoids())
                    self._getdata[pname] = driver.next()
                for tmap in plugin.snmpGetTableMaps:
                    rowSize = len(tmap.getoids())
                    maxRepetitions = max(DEFAULT_MAX_OIDS_BACK / rowSize, 1)
                    yield self.proxy.getTable(tmap.getoids(),
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
        parser = OptionParser(usage=usage)
  
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
