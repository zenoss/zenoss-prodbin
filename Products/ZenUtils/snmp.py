###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from pynetsnmp.twistedsnmp import AgentProxy


class SnmpConfig(object):
    succeeded = None
    sysName = None

    @property
    def port(self):
        return self._port

    @property
    def community(self):
        return self._community

    @property
    def weight(self):
        return self._weight is None and self.defaultWeight or self._weight


    def __init__(self, ip, weight=None, port=161, timeout=2.5, retries=2,
        community='public'):
        self._ip = ip
        self._weight = weight
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._community = community


    def __str__(self):
        return "(%s) %s:%s, SNMP%s, timeout=%ss, retries=%s, community=%s" % (
            self.weight, self._ip, self._port, self.version, self._timeout,
            self._retries, self.community)


    def getAgentProxy(self):
        return AgentProxy(
            ip=self._ip,
            port=self._port,
            timeout=self._timeout,
            tries=self._retries,
            snmpVersion=self.version,
            community=self._community)


    def test(self, oid='.1.3.6.1.2.1.1.5.0'):
        self._proxy = self.getAgentProxy()
        self._proxy.open()
        return self._proxy.get([oid]).addBoth(self.enrichResult)


    def enrichResult(self, result):
        self._proxy.close()
        if isinstance(result, dict) and bool(result):
            # one and only one key/value pair _should_ be available in result,
            # and we only need the value (the device name)
            self.sysName = result.values()[0]
            self.succeeded = True
        else:
            self.succeeded = False

        return self


class SnmpV1Config(SnmpConfig):
    version = 'v1'
    defaultWeight = 10


class SnmpV2cConfig(SnmpConfig):
    version = 'v2c'
    defaultWeight = 20


class SnmpV3Config(SnmpConfig):
    version = 'v3'
    defaultWeight = 30

    def __init__(self, ip, weight=None, port=161, timeout=2.5, retries=2,
        community='public', securityName=None, authType=None,
        authPassphrase=None, privType=None, privPassphrase=None):
        super(SnmpV3Config, self).__init__(
            ip, weight, port, timeout, retries, community)

        self._securityName = securityName
        self._authType = authType
        self._authPassphrase = authPassphrase
        self._privType = privType
        self._privPassphrase = privPassphrase


    def __str__(self):
        v3string = "securityName=%s" % self._securityName
        if self._authType:
            v3string += ", authType=%s, authPassphrase=%s" % (
                self._authType, self._authPassphrase)

        if self._privType:
            v3string += " privType=%s, privPassphrase=%s" % (
                self._privType, self._privPassphrase)

        return "(%s) %s:%s, SNMP%s, timeout=%ss, retries=%s, %s" % (
            self.weight, self._ip, self._port, self.version, self._timeout,
            self._retries, v3string)


    def getAgentProxy(self):
        cmdLineArgs = ['-u', self._securityName]

        if self._privType:
            cmdLineArgs += [
                '-l', 'authPriv',
                '-x', self._privType,
                '-X', self._privPassphrase]
        elif self._authType:
            cmdLineArgs += [
                '-l', 'authNoPriv']
        else:
            cmdLineArgs += [
                '-l', 'noAuthNoPriv']

        if self._authType:
            cmdLineArgs += [
                '-a', self._authType,
                '-A', self._authPassphrase]

        return AgentProxy(
            ip=self._ip,
            port=self._port,
            timeout=self._timeout,
            tries=self._retries,
            snmpVersion=self.version,
            community=self._community,
            cmdLineArgs=cmdLineArgs)


    def enrichResult(self, result):
        self._proxy.close()
        if isinstance(result, dict) \
            and len(result.keys()) > 0 \
            and not result.keys()[0].startswith('.1.3.6.1.6.3.15.1.1.'):
            self.sysName = result.values()[0]
            self.succeeded = True
        else:
            self.succeeded = False

        return self


class SnmpAgentDiscoverer(object):
    _bestsofar = None

    def _handleResult(self, result):
        if not hasattr(result, 'weight'):
            # http://dev.zenoss.org/trac/ticket/6268
            return

        for i, p in enumerate(self._pending):
            if p.weight == result.weight:
                self._pending.pop(i)

        if result.succeeded:
            # Record this result as the best so far.
            if self._bestsofar:
                if result.weight > self._bestsofar.weight:
                    self._bestsofar = result
            else:
                self._bestsofar = result

            # Short-circuit the rest of the tests if this result's weight is
            # higher than any still pending.
            for config in self._pending:
                if config.weight >= self._bestsofar.weight:
                    break
            else:
                if not self._d.called:
                    self._d.callback(self._bestsofar)

                return

        # We got responses to all of our queries without being able to short-
        # circuit the test. Return the best match or none.
        if len(self._pending) < 1 and not self._d.called:
            self._d.callback(self._bestsofar)


    def findBestConfig(self, configs):
        """
        Returns the best SnmpConfig in the provided configs list.
        """
        self._pending = configs
        self._d = Deferred()

        for c in configs:
            c.test().addBoth(self._handleResult)

        return self._d


if __name__ == '__main__':
    """
    The following snmpd.conf is a good one to run the following tests on.
    
    rocommunity zenosszenoss
    rouser noauthtest noauth
    createUser noauthtest MD5 "zenosszenoss"
    rouser authtest
    createUser authtest SHA "zenosszenoss"
    rouser privtest
    createUser privtest SHA "zenosszenoss" DES "zenosszenoss"
    """
    def printAndExit(result):
        print result
        reactor.stop()

    configs = [
        SnmpV3Config('127.0.0.1', weight=33, securityName='privtest',
            authType='SHA', authPassphrase='zenosszenoss',
            privType='DES', privPassphrase='zenosszenoss'),

        SnmpV3Config('127.0.0.1', weight=32, securityName='authtest',
            authType='SHA', authPassphrase='zenosszenoss'),
        
        SnmpV3Config('127.0.0.1', weight=31, securityName='noauthtest'),
        
        SnmpV2cConfig('127.0.0.1', weight=22, community='zenosszenoss'),
        SnmpV2cConfig('127.0.0.1', weight=21, community='public'),
        
        SnmpV1Config('127.0.0.1', weight=12, community='zenosszenoss'),
        SnmpV1Config('127.0.0.1', weight=11, community='public'),
        ]

    sad = SnmpAgentDiscoverer()
    sad.findBestConfig(configs).addBoth(printAndExit)
    reactor.run()
