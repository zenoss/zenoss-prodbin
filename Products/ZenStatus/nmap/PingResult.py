###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """PingResult

Utilities to parse nmap output and represent results.
"""

import collections
import math
from lxml import etree

import Globals
from zope import interface
from Products.ZenStatus import interfaces, TraceHop

_STATE_TO_STRING_MAP = { True: 'up', False: 'down'}
_NAN = float('nan')


# check nmap version!
def _checkNmapVersion(minVersion=(5,21)):
    import subprocess
    import sys
    import re
    nmap = subprocess.Popen(["nmap", "--version"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = nmap.communicate()
    if nmap.returncode:
        print >> sys.stderr, "problem running nmap!"
        print >> sys.stderr, "nmap output: %s%s" % (stdout, stderr)
        sys.exit(nmap.returncode)
    match = re.search(r"(\d+)(\.\d+){1,2}", stdout)
    if match is None:
        print >> sys.stderr, "could not detect nmap version"
        print >> sys.stderr, "nmap output: %s%s" % (stdout, stderr)
        sys.exit(nmap.returncode)
    version = [int(i) for i in match.group(0).split(".")]
    if tuple(version) < tuple(minVersion):
        print >> sys.stderr, "detected nmap %r, mininum version %r" % (
            version, minVersion)
        sys.exit(1)

_checkNmapVersion()

def parseNmapXml(input):
    """
    Parse the XML output of nmap and return a list PingResults.
    """
    results = []
    parseTree = etree.parse(input)
    for hostTree in parseTree.xpath('/nmaprun/host'):
        result = PingResult(hostTree)
        results.append(result)
    return (results)
    
def parseNmapXmlToDict(input):
    """
    Parse the XML output of nmap and return a dict of PingResults indexed by IP.
    """
    rdict = {}
    for result in parseNmapXml(input):
        rdict[result.address] = result
    return rdict


class PingResult(object):
    """
    Model of an nmap ping/traceroute result.
    """
    interface.implements(interfaces.IPingResult)

    def __init__(self, hostTree):
        """
        Contruct an PingResult from an XML parse tree for a host entry.
        """
        if getattr(hostTree, 'xpath', None) is None:
            raise ValueError("hostTree must be of lxml.etree.Element type")
        self._timestamp = self._parseTimestamp(hostTree)
        self._address = self._parseAddress(hostTree)
        self._isUp = self._parseState(hostTree)
        if self._isUp:
            self._rtt, self._rttVariance = self._parseTimes(hostTree)
            self._trace = self._parseTraceroute(hostTree)
        else:
            self._rtt, self._rttVariace = (_NAN, _NAN)
            self._trace = tuple()
    
    def _parseTimestamp(self, hostTree):
        """
        Extract timestamp if it exists.
        """
        try:
            starttime = hostTree.attrib['starttime']
            timestamp = int(starttime)
            return timestamp
        except Exception as ex:
            return None

    def _parseTimes(self, hostTree):
        """
        Extract round trip time from the hostTree.
        """
        times = hostTree.xpath('times')
        if len(times) != 1:
            raise ValueError("no times found for hostTree")
        timesNode = times[0]
        rtt = timesNode.attrib['srtt']
        rtt = float(rtt) / 1000.0 # given in milli sec, convert to secs
        rttVariance = timesNode.attrib['rttvar']
        rttVariance = float(rttVariance) / 1000.0
        return (rtt, rttVariance)
        
    def _parseAddress(self, hostTree):
        """
        Extract the address (ip) from the hostTree.
        """
        
        addressNodes = hostTree.xpath('address')
        if len(addressNodes) != 1:
            raise ValueError("hostTree does not have address node")
        addressNode = addressNodes[0]
        address = addressNode.attrib['addr']
        return address

    def _parseState(self, hostTree):
        """
        Extract the host status from hostTree: return True if up, False if down.
        """
        statusNodes = hostTree.xpath('status')
        if len(statusNodes) != 1:
            raise ValueError("hostTree does not have status node")
        statusNode = statusNodes[0]
        state = statusNode.attrib['state']
        if state == 'up':
            return True
        if state == 'down':
            return False
        raise ValueError("hostTree/status.state has uknown value %s" % state)
    
    def _parseTraceroute(self, hostTree):
        """
        Extract the traceroute hops from hostTree in to a list that
        preserves the hop order and saves the hop rtt.
        """
        hops = []
        traceNodes = hostTree.xpath('trace')
        if len(traceNodes) != 1:
            return tuple()  # no traceroute info in output file
        traceNode = traceNodes[0]
        hopNodes = traceNode.xpath('hop')
        if len(hopNodes) < 1:
            raise ValueError("hostTree does not have a trace/hop nodes")
        for hopNode in hopNodes:
            ipaddr = hopNode.attrib['ipaddr']
            rtt = float(hopNode.attrib['rtt'])
            hops.append(TraceHop(ip=ipaddr, rtt=rtt))
        return hops
    
    @property
    def timestamp(self):
        """Timestamp of when ping was returned (seconds since epoch)."""
        return self._timestamp

    @property
    def address(self):
        """Address of the host"""
        return self._address
    
    @property
    def trace(self):
        """traceroute of the host"""
        return tuple(self._trace)
    
    def getStatusString(self):
        """status string: up or down"""
        return _STATE_TO_STRING_MAP[self._isUp]
    
    def __repr__(self):
        return "PingResult [%s, %s]" % (self._address, self.getStatusString())
        
    @property
    def isUp(self):
        """true if host is up, false if host is down"""
        return self._isUp

    @property
    def rtt(self):
        """round trip time aka ping time aka rtt; nan if host was down"""
        return self._rtt

    @property
    def variance(self):
        """variance of the rtt; nan if host was down"""
        return self._rttVariance

    @property
    def stdDeviation(self):
        """standard deviation of the rtt; nan if host was down"""
        math.sqrt(self._rttVariance)

if __name__ == '__main__':
    
    import os.path
    nmap_testfile = os.path.dirname(
        os.path.realpath(__file__)) + '/tests/nmap_ping.xml'
    results = parseNmapXml(nmap_testfile)
    for result in results:
        print result
        for hop in result.trace:
            print "  ->", hop
