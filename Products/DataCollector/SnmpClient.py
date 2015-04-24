##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
import logging
log = logging.getLogger("zen.SnmpClient")

from twisted.internet import reactor, error, defer
from twisted.python import failure
from twisted.internet.error import TimeoutError

from Products.ZenUtils.snmp import SnmpV1Config, SnmpV2cConfig
from Products.ZenUtils.snmp import SnmpAgentDiscoverer

from pynetsnmp.twistedsnmp import snmpprotocol, Snmpv3Error

from Products.ZenUtils.Driver import drive

import zope.component

from Products.ZenCollector.interfaces import IEventService
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp

global defaultTries, defaultTimeout
defaultTries = 2
defaultTimeout = 1
defaultSnmpCommunity = 'public'

DEFAULT_MAX_OIDS_BACK = 40

STATUS_EVENT = {'eventClass' : Status_Snmp, 'eventGroup' : 'SnmpTest'}

from BaseClient import BaseClient

class SnmpClient(BaseClient):

    def __init__(self, hostname, ipaddr, options=None, device=None,
                 datacollector=None, plugins=[]):
        BaseClient.__init__(self, device, datacollector)
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
        self.proxy = None
        self._eventService = zope.component.queryUtility(IEventService)

    def initSnmpProxy(self):
        if self.proxy is not None: self.proxy.close()
        srcport = snmpprotocol.port()
        self.proxy = self.connInfo.createSession(srcport.protocol)
        self.proxy.open()

    def run(self):
        """Start snmp collection.
        """
        log.debug("Starting %s", self.connInfo.summary())
        self.initSnmpProxy()
        drive(self.doRun).addBoth(self.clientFinished)


    # FIXME: cleanup --force option #2660
    def checkCiscoChange(self, driver):
        """Check to see if a cisco box has changed.
        """
        device = self.device
        yield self.proxy.get(['.1.3.6.1.4.1.9.9.43.1.1.1.0'])
        lastpolluptime = device.getLastPollSnmpUpTime()
        log.debug("lastpolluptime = %s", lastpolluptime)
        result = True
        try:
            lastchange = driver.next().values()[0]
            log.debug("lastchange = %s", lastchange)
            if lastchange <= lastpolluptime:
                log.info("skipping cisco device %s no change detected",
                         device.id)
                result = False
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except Exception:
            pass
        yield defer.succeed(result)


    def doRun(self, driver):
        # test snmp connectivity
        log.debug("Testing SNMP configuration")
        yield self.proxy.walk('.1.3')
        try:
            driver.next()
        except TimeoutError:
            log.info("Device timed out: " + self.connInfo.summary())
            if self.options.discoverCommunity:
                yield self.findSnmpCommunity()
                snmp_config = driver.next()
                if not snmp_config:
                    log.warn(
                        'Failed to rediscover the SNMP connection info for %s',
                        self.device.manageIp)
                    return
                if snmp_config.version:
                    self.connInfo.zSnmpVer = snmp_config.version
                if snmp_config.port:
                    self.connInfo.zSnmpPort = snmp_config.port
                if snmp_config.community:
                    self.connInfo.zSnmpCommunity = snmp_config.community
                self.connInfo.changed = True
                self.initSnmpProxy()
            else:
                return
        except Snmpv3Error:
            log.info("Cannot connect to SNMP agent: {0}".format(self.connInfo.summary()))
            return
        except Exception:
            log.exception("Unable to talk: " + self.connInfo.summary())
            return

        changed = True
        # FIXME: cleanup --force option #2660
        if not self.options.force and self.device.snmpOid.startswith(".1.3.6.1.4.1.9"):
            yield drive(self.checkCiscoChange)
            changed = driver.next()
        if changed:
            yield drive(self.collect)

    def findSnmpCommunity(self):
        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            """
            log.info("Rediscovering SNMP connection info for %s",
                        self.device.id)

            communities = list(self.device.zSnmpCommunities)
            communities.reverse()

            ports = self.device.zSnmpDiscoveryPorts
            ports = ports if ports else [self.device.zSnmpPort]

            configs = []
            weight = 0
            for community in communities:
                for port in ports:
                    weight+=1
                    port = int(port)
                    configs.append(SnmpV1Config(
                        self.device.manageIp, weight=weight,
                        port=port,
                        timeout=self.connInfo.zSnmpTimeout,
                        retries=self.connInfo.zSnmpTries,
                        community=community))
                    configs.append(SnmpV2cConfig(
                        self.device.manageIp, weight=weight+1000, port=port,
                        timeout=self.connInfo.zSnmpTimeout,
                        retries=self.connInfo.zSnmpTries,
                        community=community))

            yield SnmpAgentDiscoverer().findBestConfig(configs)
            driver.next()
        return drive(inner)


    def collect(self, driver):
        maxOidsPerRequest = getattr(self.device, 'zMaxOIDPerRequest', DEFAULT_MAX_OIDS_BACK)
        log.debug("Using a max of %s OIDs per request", maxOidsPerRequest)
        for plugin in self.plugins:
            try:
                log.debug('running %s', plugin)
                pname = plugin.name()
                self._tabledata[pname] = {}
                log.debug("sending queries for plugin %s", pname)
                if plugin.snmpGetMap:
                    results = {}
                    for oid in plugin.snmpGetMap.getoids():
                        yield self.proxy.get([oid])
                        results.update(driver.next())
                    self._getdata[pname] = results
                for tmap in plugin.snmpGetTableMaps:
                    rowSize = len(tmap.getoids())
                    maxRepetitions = max(maxOidsPerRequest / rowSize, 1)
                    yield self.proxy.getTable(tmap.getoids(),
                                              maxRepetitions=maxRepetitions,
                                              limit=sys.maxint)
                    self._tabledata[pname][tmap] = driver.next()
            except Exception, ex:
                if not isinstance( ex, error.TimeoutError ):
                    log.exception("device %s plugin %s unexpected error",
                                  self.hostname, pname)


    def getResults(self):
        """Return data for this client in the form
        ((plugin, (getdata, tabledata),)
        getdata = {'.1.2.4.5':"value",}
        tabledata = {tableMap : {'.1.2.3.4' : {'.1.2.3.4.1': "value",...}}}
        """
        data = []
        for plugin in self.plugins:
            pname = plugin.name()
            getdata = self._getdata.get(pname,{})
            tabledata = self._tabledata.get(pname,{})
            if getdata or tabledata:
                data.append((plugin, (getdata, tabledata)))
        return data

    def _sendStatusEvent(self, summary, eventKey=None, severity=Event.Error):
        self._eventService.sendEvent(STATUS_EVENT.copy(), severity=severity, device=self.device.id,
                                     eventKey=eventKey, summary=summary)

    def clientFinished(self, result):
        log.info("snmp client finished collection for %s" % self.hostname)
        if isinstance(result, failure.Failure):
            from twisted.internet import error
            if isinstance(result.value, error.TimeoutError):
                log.warning("Device %s timed out: are "
                            "your SNMP settings correct?", self.hostname)
                summary = "SNMP agent down - no response received"
                log.info("Sending event: %s", summary)
                self._sendStatusEvent(summary, eventKey='agent_down')
            elif isinstance(result.value, Snmpv3Error):
                log.warning("Connection to device {0.hostname} failed: {1.value.message}".format(self, result))
            else:
                log.exception("Device %s had an error: %s",self.hostname,result)
        else:
            self._sendStatusEvent('SNMP agent up', eventKey='agent_down', severity=Event.Clear)
        self.proxy.close()
        """tell the datacollector that we are all done"""
        if self.datacollector:
            self.datacollector.clientFinished(self)
        else:
            reactor.stop()

    def stop(self):
        self.proxy.close()

