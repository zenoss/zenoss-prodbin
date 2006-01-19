import os
import re
import threading
import pprint
import logging
slog = logging.getLogger("zen.Syslog")

from Event import Event
from syslog_h import *

# Regular expressions that parse syslog tags from different sources
parsers = (
# cisco msg with card inicator
r"%CARD-\S+:(SLOT\d+) %(?P<eventClassKey>\S+): (?P<summary>.*)",

# cisco standard msg
r"%(?P<eventClass>\S+): (?P<summary>.*)",

# ntsyslog msg
r"(?P<component>\S+)\[(?P<ntseverity>\D+)\] (?P<ntevid>\d+) (?P<summary>.*)",

# unix syslog with pid
r"(?P<component>\S+)\[(?P<pid>\d+)\]: (?P<summary>.*)",

# unix syslog without pid
r"(?P<component>\S+): (?P<summary>.*)",

) 

# compile regex parsers on load
compiledParsers = []
for regex in parsers:
    compiledParsers.append(re.compile(regex)) 


class SyslogEvent(Event):

    agent="ZenSyslog"
    eventGroup="Syslog" 

    def getDedupFields(self, default):
        """Return list of dedupid fields.
        """
        default = list(default)
        if not getattr(self, "eventKey", False):
            default.append("summary")
        return default




class SyslogProcessingThread(threading.Thread):
    """
    This class does the actual processing of a syslog message.
    """

    def __init__(self, master, msg, ipaddress, hostname, parsehost): 
        threading.Thread.__init__(self)
        self.setDaemon(1)
        self.master = master
        self.msg = msg
        self.ipaddress = ipaddress
        self.hostname = hostname
        self.parsehost = parsehost


    def run(self):
        """Peform event processing after event is recieved.
        """
        try:
            evt = SyslogEvent(device=self.hostname, ipAddress=self.ipaddress)
            slog.debug("hostname=%s, ip=%s", self.hostname, self.ipaddress)
            slog.debug(self.msg)

            evt, msg = self.parsePRI(evt, self.msg) 
            if evt.priority > self.master.minpriority: return

            evt, msg = self.parseHEADER(evt, msg)
            evt = self.parseTag(evt, msg) #rest of msg now in summary of event
            evt = self.buildEventClassKey(evt)
            zem=None
            try:
                zem = self.master.getZem()
                zem.sendEvent(evt)
            finally:
                if zem: 
                    zem._p_jar.close()
                    del zem
        except:
            slog.exception("event processing failure: %s", self.hostname)

    
    def parsePRI(self, evt, msg):
        """
        Parse RFC-3164 PRI part of syslog message to get facility and priority.
        """
        pri = None
        fac = None
        if msg[:1] == '<':
            pos = msg.find('>')
            fac, pri = LOG_UNPACK(int(msg[1:pos]))
            msg = msg[pos+1:]
        elif msg and msg[0] < ' ':
            fac, pri = LOG_KERN, ord(msg[0])
            msg = msg[1:]
        evt.facility = fac_names.get(fac,"unknown")
        evt.priority = pri
        evt.severity = self.defaultSeverityMap(pri)
        slog.debug("fac=%s pri=%s", fac, pri)
        slog.debug("facility=%s severity=%s", evt.facility, evt.severity)
        return evt, msg


    def defaultSeverityMap(self, pri):
        """Default mapping from syslog priority to severity.
        """
        sev = 1
        if pri < 3: sev = 5
        elif pri == 3: sev = 4
        elif pri == 4: sev = 3
        elif 7 < pri > 4: sev = 2
        return sev


    timeParse = \
        re.compile("^(\S{3} [\d ]{2} [\d ]{2}:[\d ]{2}:[\d ]{2}) (.*)").search
    notHostSearch = re.compile("[-\[:]").search
    def parseHEADER(self, evt, msg):
        """Parse RFC-3164 HEADER part of syslog message.  TIMESTAMP format is:
        MMM HH:MM:SS and host is next token without the characters '[' or ':'.
        """
        slog.debug(msg)
        m = self.timeParse(msg)
        if m: 
            slog.debug("parseHEADER timestamp=%s", m.group(1))
            #FIXME date parsing in event not working
            #evt.initTime(m.group(1))
            evt.originalTime = m.group(1)
            msg = m.group(2).strip()
        msglist = msg.split()
        if self.parsehost and not self.notHostSearch(msglist[0]):
            evt.hostname = msglist[0]
            slog.debug("parseHEADER hostname=%s", evt.hostname)
            msg = " ".join(msglist[1:])
        return evt, msg


    def parseTag(self, evt, msg):
        """Parse the RFC-3164 tag of the syslog message using the regex defined
        at the top of this module.
        """
        slog.debug(msg)
        for regex in compiledParsers:        
            m = regex.search(msg)
            if not m: continue
            slog.debug("tag match: %s", m.groupdict())
            evt.updateFromDict(m.groupdict())
            break
        else:
            slog.warn("parseTag failed")
            evt.summary = msg
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
            evt.eventClassKey = "%s_%s" % (evt.component,evt.ntevid)
        elif hasattr(evt, 'component'):
            evt.eventClassKey = evt.component
        if hasattr(evt, 'eventClassKey'): 
            slog.debug("eventClassKey=%s", evt.eventClassKey)
        else:
            slog.debug("no eventClassKey assigned")
        return evt


    def applyDeviceContext(self, device, evt):
        """
        Apply event attributes from device context.  List of attribute names is
        looked for in zProperty 'zEventProperties'. These attributes are 
        looked up using the key 'zEvent_'+attr name (to prevent name clashes). 
        Any non-None attribute values are applied to the event.
        """
        evt.prodState = device.productionState
        evt.Location = device.getLocationName()
        evt.DeviceClass  = device.getDeviceClassName()
        evt.DeviceGroups = "|"+"|".join(device.getDeviceGroupNames())
        evt.Systems = "|"+"|".join(device.getSystemNames())
        attnames = getattr(device, "zEventProperties", ())
        for attr in attnames:
            attkey = "zEvent_" + attr
            value = getattr(device, attkey, None)
            if value != None:
                setattr(evt, attr, value)
        return evt


