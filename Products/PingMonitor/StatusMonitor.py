#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""StatusMonitor

Base class for makeing deamon programs

$Id: StatusMonitor.py,v 1.9 2003/08/29 20:33:10 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import signal
import os
import sys
import socket
import time

from Products.ZenUtils.ZenDaemon import ZenDaemon

class StatusMonitor(ZenDaemon):
    
    def __init__(self):
        ZenDaemon.__init__(self)
        self.dnstries = 3
        self.forwarddnscache = {}
        self.reversednscache = {}


    def forwardDnsLookup(self, hostname):
        """try the forward lookup dnstries times if it fails look in cache"""
        try:
            ip = self._dnsLookup(socket.gethostbyname, hostname)
            self.forwarddnscache[hostname] = ip
            return ip
        except socket.error:
            if self.forwarddnscache.has_key(hostname):
                return self.forwarddnscache[hostname]
            else:
                raise


    def reverseDnsLookup(self, ip):
        """try the reverse lookup dnstries times if it fails look in cache"""
        try:
            hostname = self._dnsLookup(socket.gethostbyaddr, ip)
            self.reversednscache[hostname] = ip
            return ip
        except socket.error:
            if self.reversednscache.has_key(hostname):
                return self.reversednscache[hostname]
            else:
                raise


    def _dnsLookup(self, function, target):
        """try dns lookup dnstries times"""
        ip = None
        i=0
        while 1: 
            try:
                i+=1
                ip = function(target)
            except socket.error:
                if i > self.getDnsTries():
                    raise 
            if ip: break
        return ip
        

    def getDnsTries(self):
        if not hasattr(self, 'dnstries'):
            self.dnstries=3
        return self.dnstries

        
    def getConfig(self):
        """handle errors when loading config from server
        we try configtries times if no previous config is found"""
        for i in range(self.options.configtries):
            try:
                self.loadConfig()
                return
            except SystemExit: raise
            except:
                if self.validConfig():
                    self.log.exception(
                    "configuration load exception using previous configuration")
                    return
                else:
                    self.log.exception('config load failed')
                    if i <= (self.options.configtries - 2):
                        self.log.warn(
                            "initial config load failed will retry")
                        time.sleep(self.options.configsleep)
                    else:
                        self.log.critical(
                            "initial config load failed %d times exiting"
                                    % self.options.configtries)
                        sys.exit(2)


    def buildOptions(self):
        ZenDaemon.buildOptions(self)
        self.parser.add_option('-T', '--configtries',
                    dest='configtries',
                    default=5,
                    action="store",
                    help="How many times to retry config connection")
        self.parser.add_option('-S', '--configsleep',
                    dest='configsleep',
                    default=20,
                    action="store",
                    help="How long to sleep between config connections")
