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

__doc__='''SyslogProcessing

Class for turning syslog events into Zenoss Events

'''

import re
import logging
slog = logging.getLogger("zen.Syslog")

import Globals
from Products.ZenEvents.syslog_h import *

import socket

# Regular expressions that parse syslog tags from different sources
parsers = (
    
# ntsyslog windows msg
r"^(?P<component>.+)\[(?P<ntseverity>\D+)\] (?P<ntevid>\d+) (?P<summary>.*)",

# cisco msg with card inicator
r"%CARD-\S+:(SLOT\d+) %(?P<eventClassKey>\S+): (?P<summary>.*)",

# cisco standard msg
r"%(?P<eventClassKey>(?P<component>\S+)-\d-\S+): (?P<summary>.*)",

# Cisco ACS
r"^(?P<ipAddress>\S+)\s+(?P<summary>(?P<eventClassKey>CisACS_\d\d_\S+)\s+(?P<eventKey>\S+)\s.*)",

# netscreen device msg
r"device_id=\S+\s+\[\S+\](?P<eventClassKey>\S+\d+):\s+(?P<summary>.*)\s+\((?P<originalTime>\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)\)",

# unix syslog with pid
r"(?P<component>\S+)\[(?P<pid>\d+)\]:\s*(?P<summary>.*)",

# unix syslog without pid
r"(?P<component>\S+): (?P<summary>.*)",

# adtran devices
r"^(?P<deviceModel>[^\[]+)\[(?P<deviceManufacturer>ADTRAN)\]:(?P<component>[^\|]+\|\d+\|\d+)\|(?P<summary>.*)",

# proprietary message passing system
r"^(?P<component>\S+) (LOG|RSE) \d \S+ \d\d:\d\d:\d\d-\d\d:\d\d:\d\d \d{5} \d{2} \d{5} \S+ \d{4} \d{5} - (?P<summary>.*) \d{4} \d{4}",
) 

# compile regex parsers on load
compiledParsers = []
for regex in parsers:
    compiledParsers.append(re.compile(regex)) 


class SyslogProcessor(object):

    def __init__(self,sendEvent,minpriority,parsehost,monitor,defaultPriority): 
        self.minpriority = minpriority
        self.parsehost = parsehost
        self.sendEvent = sendEvent
        self.monitor = monitor
        self.defaultPriority = defaultPriority


    def process(self, msg, ipaddr, host, rtime):
        evt = dict(device=host,
                   ipAddress=ipaddr,
                   firstTime=rtime,
                   lastTime=rtime,
                   eventGroup='syslog')
        slog.debug("host=%s, ip=%s", host, ipaddr)
        slog.debug(msg)

        evt, msg = self.parsePRI(evt, msg) 
        if evt['priority'] > self.minpriority: return

        evt, msg = self.parseHEADER(evt, msg)
        evt = self.parseTag(evt, msg) 
        #rest of msg now in summary of event
        evt = self.buildEventClassKey(evt)
        evt['monitor'] = self.monitor
        self.sendEvent(evt)

        
    def parsePRI(self, evt, msg):
        """
        Parse RFC-3164 PRI part of syslog message to get facility and priority.
        """
        pri = self.defaultPriority
        fac = None
        if msg[:1] == '<':
            pos = msg.find('>')
            fac, pri = LOG_UNPACK(int(msg[1:pos]))
            msg = msg[pos+1:]
        elif msg and msg[0] < ' ':
            fac, pri = LOG_KERN, ord(msg[0])
            msg = msg[1:]
        evt['facility'] = fac_names.get(fac,"unknown")
        evt['priority'] = pri
        evt['severity'] = self.defaultSeverityMap(pri)
        slog.debug("fac=%s pri=%s", fac, pri)
        slog.debug("facility=%s severity=%s", evt['facility'], evt['severity'])
        return evt, msg


    def defaultSeverityMap(self, pri):
        """Default mapping from syslog priority to severity.
        """
        sev = 1
        if pri < 3: sev = 5
        elif pri == 3: sev = 4
        elif pri == 4: sev = 3
        elif pri == 5 or pri == 6: sev = 2
        return sev


    timeParse = \
        re.compile("^(\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[\d ]{2}) (.*)").search
    notHostSearch = re.compile("[\[:]").search
    def parseHEADER(self, evt, msg):
        """Parse RFC-3164 HEADER part of syslog message.  TIMESTAMP format is:
        MMM HH:MM:SS and host is next token without the characters '[' or ':'.
        """
        slog.debug(msg)
        m = self.timeParse(msg)
        if m: 
            slog.debug("parseHEADER timestamp=%s", m.group(1))
            evt['originalTime'] = m.group(1)
            msg = m.group(2).strip()
        msglist = msg.split()
        if self.parsehost and not self.notHostSearch(msglist[0]):
            device = msglist[0]
            if device.find('@') >= 0:
                device = device.split('@', 1)[1]
            try:
                evt['ipAddress'] = socket.gethostbyname(device)
            except socket.error:
                pass
            slog.debug("parseHEADER hostname=%s", evt['device'])
            msg = " ".join(msglist[1:])
            evt['device'] = device
        return evt, msg


    def parseTag(self, evt, msg):
        """Parse the RFC-3164 tag of the syslog message using the regex defined
        at the top of this module.
        """
        slog.debug(msg)
        for parser in compiledParsers:        
            slog.debug("tag regex: %s", parser.pattern)
            m = parser.search(msg)
            if not m: continue
            slog.debug("tag match: %s", m.groupdict())
            evt.update(m.groupdict())
            break
        else:
            slog.warn("parseTag failed:'%s'", msg)
            evt['summary'] = msg
        return evt


    def buildEventClassKey(self, evt):
        """Build the key used to find an events dictionary record. If eventClass
        is defined it is used. For NT events "Source_Evid" is used. For other
        syslog events we use the summary of the event to perform a full text
        or'ed search.
        """
        if hasattr(evt, 'eventClassKey') or hasattr(evt, 'eventClass'):
            return evt
        elif hasattr(evt, 'ntevid'):
            evt['eventClassKey'] = "%s_%s" % (evt['component'],evt['ntevid'])
        elif hasattr(evt, 'component'):
            evt['eventClassKey'] = evt['component']
        if hasattr(evt, 'eventClassKey'): 
            slog.debug("eventClassKey=%s", evt['eventClassKey'])
            try:
                evt['eventClassKey'] = evt['eventClassKey'].decode('latin-1')
            except:
                evt['eventClassKey'] = evt['eventClassKey'].decode('utf-8')
        else:
            slog.debug("no eventClassKey assigned")
        return evt
