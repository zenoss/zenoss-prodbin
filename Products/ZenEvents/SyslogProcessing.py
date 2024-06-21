##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """SyslogProcessing
Class for turning syslog events into Zenoss Events
"""

import re
import logging
slog = logging.getLogger("zen.Syslog")
import socket

from copy import deepcopy
from Products.ZenEvents.syslog_h import *
from Products.ZenUtils.IpUtil import isip


class SyslogProcessor(object):
    """
    Class to process syslog messages and convert them into events viewable
    in the Zenoss event console.
    """

    def __init__(self,sendEvent,minpriority,parsehost,monitor,defaultPriority,syslogParsers,syslogSummaryToMessage):
        """
        Initializer

        @param sendEvent: message from a remote host
        @type sendEvent: string
        @param minpriority: ignore anything under this priority
        @type minpriority: integer
        @param parsehost: hostname where this parser is running
        @type parsehost: string
        @param monitor: name of the distributed collector monitor
        @type monitor: string
        @param defaultPriority: priority to use if it can't be understood from the received packet
        @type defaultPriority: integer
        @param syslogParsers: configureable syslog parsers
        @type defaultPriority: list
        """
        self.minpriority = minpriority
        self.parsehost = parsehost
        self.sendEvent = sendEvent
        self.monitor = monitor
        self.defaultPriority = defaultPriority
        self.compiledParsers = []
        self.updateParsers(syslogParsers)
        self.syslogSummaryToMessage = syslogSummaryToMessage

    def updateParsers(self, parsers):
        self.compiledParsers = deepcopy(parsers)
        for i, parserCfg in enumerate(self.compiledParsers):
            if 'expr' not in parserCfg:
                msg = 'Parser configuration #{} missing a "expr" attribute'.format(i)
                slog.warn(msg)
                self.syslogParserErrorEvent(message=msg)
                continue            
            try:
                parserCfg['expr'] = re.compile(parserCfg['expr'], re.DOTALL)
            except Exception as ex:
                msg = 'Parser configuration #{} Could not compile expression "{!r}", {!r}'.format(i, parserCfg['expr'], ex)
                slog.warn(msg)
                self.syslogParserErrorEvent(message=msg)
                pass

    def syslogParserErrorEvent(self, **kwargs):
        """
        Build an Event dict from parameters.n
        """
        eventDict = {
            'device': '127.0.0.1',
            'eventClass': '/App/Zenoss',
            'severity': 4,
            'eventClassKey': '',
            'summary': 'Syslog Parser processing issue',
            'component': 'zensyslog'
        }
        if kwargs:
            eventDict.update(kwargs)
        self.sendEvent(eventDict)

    def process(self, msg, ipaddr, host, rtime):
        """
        Process an event from syslog and convert to a Zenoss event

        @param msg: message from a remote host
        @type msg: string
        @param ipaddr: IP address of the remote host
        @type ipaddr: string
        @param host: remote host's name
        @type host: string
        @param rtime: time as reported by the remote host
        @type rtime: string
        """
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
        if evt == "ParserDropped":
            return evt
        elif evt:
            # Cisco standard msg includes the severity in the tag
            if 'overwriteSeverity' in evt.keys():
                old_severity = evt['severity']
                new_severity = self.defaultSeverityMap(int(evt['overwriteSeverity']))
                evt['severity'] = new_severity
                slog.debug('Severity overwritten in message tag. Previous:%s Current:%s', old_severity, new_severity)
            #rest of msg now in summary of event
            evt = self.buildEventClassKey(evt)
            evt['monitor'] = self.monitor
            if 'message' not in evt:
                evt['message'] = msg
            # Convert strings to unicode, previous code converted 'summary' &
            # 'message' fields. With parsing group name matching, good idea to
            # convert all fields.
            evt.update({k: unicode(v) for k,v in evt.iteritems() if isinstance(v, str)})
            self.sendEvent(evt)
            return "EventSent"
        else:
            return None


    def parsePRI(self, evt, msg):
        """
        Parse RFC-3164 PRI part of syslog message to get facility and priority.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: tuple of dictionary of event properties and the message
        @type: (dictionary, string)
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
        evt['facility'] = fac
        evt['priority'] = pri
        evt['severity'] = self.defaultSeverityMap(pri)
        slog.debug("fac=%s pri=%s", fac, pri)
        slog.debug("facility=%s severity=%s", evt['facility'], evt['severity'])
        return evt, msg


    def defaultSeverityMap(self, pri):
        """
        Default mapping from syslog priority to severity.

        @param pri: syslog priority from host
        @type pri: integer
        @return: numeric severity
        @type: integer
        """
        sev = 1
        if pri < 3: sev = 5
        elif pri == 3: sev = 4
        elif pri == 4: sev = 3
        elif pri == 5 or pri == 6: sev = 2
        return sev


    timeParse = \
        re.compile("^(\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[\d ]{2}(?:\.\d{1,3})?) (.*)", re.DOTALL).search
    notHostSearch = re.compile("[\[:]").search
    def parseHEADER(self, evt, msg):
        """
        Parse RFC-3164 HEADER part of syslog message.  TIMESTAMP format is:
        MMM HH:MM:SS and host is next token without the characters '[' or ':'.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: tuple of dictionary of event properties and the message
        @type: (dictionary, string)
        """
        slog.debug(msg)
        m = re.sub("Kiwi_Syslog_Daemon \d+: \d+: "
            "\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[^:]+: ", "", msg)
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
            slog.debug("parseHEADER hostname=%s", evt['device'])
            msg = " ".join(msglist[1:])
            evt['device'] = device
            if isip(device):
                evt['ipAddress'] = device
            else:
                if 'ipAddress' in evt:
                    del(evt['ipAddress'])
        return evt, msg


    def parseTag(self, evt, msg):
        """
        Parse the RFC-3164 tag of the syslog message using the regex defined
        at the top of this module.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @param msg: message from host
        @type msg: string
        @return: dictionary of event properties
        @type: dictionary
        """
        slog.debug(msg)
        for i, parserCfg in enumerate(self.compiledParsers):
            slog.debug("parserCfg[%s] regex: %s", i, parserCfg['expr'].pattern)
            m = parserCfg['expr'].search(msg)
            if not m:
                continue
            elif not parserCfg['keep']:
                slog.debug("parserCfg[%s] matched but DROPPED due to parserCfg. msg:%r, pattern:%r, parsedGroups:%r",
                    i,
                    msg,
                    parserCfg['expr'].pattern,
                    m.groupdict())
                return "ParserDropped"
            slog.debug("parserCfg[%s] matched. msg:%r, pattern:%r, parsedGroups:%r",
                i,
                msg,
                parserCfg['expr'].pattern,
                m.groupdict())
            evt.update(m.groupdict())
            evt['parserRuleMatched'] = i
            break
        else:
            slog.debug("No matching parser: %r", msg)
            evt['summary'] = msg
        if self.syslogSummaryToMessage:
            # In case the parsed event doesn't have a summary we set an empty string to the message key
            evt['message'] = evt.get("summary", "")
            evt['unparsedMessage'] = msg
        return evt


    def buildEventClassKey(self, evt):
        """
        Build the key used to find an events dictionary record. If eventClass
        is defined it is used. For NT events "Source_Evid" is used. For other
        syslog events we use the summary of the event to perform a full text
        or'ed search.

        @param evt: dictionary of event properties
        @type evt: dictionary
        @return: dictionary of event properties
        @type: dictionary
        """
        if 'eventClassKey' in evt or 'eventClass' in evt:
            return evt
        elif 'ntevid' in evt:
            evt['eventClassKey'] = "%s_%s" % (evt['component'],evt['ntevid'])
        elif 'component' in evt:
            evt['eventClassKey'] = evt['component']
        if 'eventClassKey' in evt:
            slog.debug("eventClassKey=%s", evt['eventClassKey'])
            try:
                evt['eventClassKey'] = evt['eventClassKey'].decode('latin-1')
            except Exception:
                evt['eventClassKey'] = evt['eventClassKey'].decode('utf-8')
        else:
            slog.debug("No eventClassKey assigned")
        return evt
