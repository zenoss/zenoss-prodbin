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
log = logging.getLogger("zen.WinEventlog")

from Products.ZenEvents.ZenEventClasses import Status_Wmi

class WinEventlog(object):

    agent = name = "zeneventlog"
    manager = socket.getfqdn()
    evtAlertGroup = "Eventlog"
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
        evt['agent'] = self.agent
        evt['severity'] = sev
        evt['eventGroup'] = self.evtAlertGroup
        evt['manager'] = self.manager
        evt['eventClass'] = Status_Wmi
        log.debug("device:%s msg:'%s'", srec.name, lrec.Message)
        return evt
