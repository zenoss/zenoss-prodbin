#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import socket
import logging
log = logging.getLogger("zen.WinEventlog")

class WinEventlog(object):

    name = "WinEventlog"
    manager = socket.getfqdn()
    evtAgent = "WinEventlog"
    evtAlertGroup = "Eventlog"
    failure = {'eventClass':'/Status/WinEventlog', 'agent': 'zenwin',
                'severity':4}
    statmsg = "Windows Service '%s' is %s"
    
    eventlogFields = "EventCode,EventType,Message,SourceName,TimeGenerated"

    minSeverity = 2

    
    def run(self, srec, zem):
        """Test a single device.
        """
        wql = "select LogFileName from Win32_NTEventLogFile"
        for linfo in srec.query(wql):
            logname = linfo.LogFileName
            if logname == "Security": continue # don't monitor for now
            lastpoll = srec.lastpoll.get(logname, None)
            if lastpoll is None:
                lastpoll = srec.instance("Win32_OperatingSystem").LocalDateTime
                srec.lastpoll[logname] = lastpoll
                log.info("first time seeing log %s device %s",logname,srec.name)
                continue
            wql = ("select %s from Win32_NTLogEvent where LogFile='%s' "
                  "and TimeGenerated > '%s' and EventType <= %d" % 
                  (self.eventlogFields, logname, lastpoll, self.minSeverity))
            log.debug(wql)
            for i, lrec in enumerate(srec.query(wql)):
                if i == 0: srec.lastpoll[logname] = lrec.TimeGenerated
                if not lrec.Message: continue
                evt = self.mkevt(srec, lrec)
                zem.sendEvent(evt)

    
    def mkevt(self, srec, lrec):
        """Put event in the queue to be sent to the ZenEventManager.
        """
        evtkey = "%s_%s" % (lrec.SourceName, lrec.EventCode)
        sev = 4 - lrec.EventType     #lower severity by one level
        evt = {}
        evt['device'] = srec.name
        evt['eventClassKey'] = evtkey
        evt['eventGroup'] = lrec.LogFile
        evt['component'] = lrec.SourceName
        evt['ntevid'] = lrec.EventCode
        evt['summary'] = lrec.Message.strip()
        evt['agent'] = self.evtAgent
        evt['severity'] = sev
        evt['eventGroup'] = self.evtAlertGroup
        evt['manager'] = self.manager
        log.debug("device:%s msg:'%s'", srec.name, lrec.Message)
        return evt
