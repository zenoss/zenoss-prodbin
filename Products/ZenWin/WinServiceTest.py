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
log = logging.getLogger("zen.WinServiceTest")

class WinServiceTest(object):
    
    name = "WinServiceTest"
    manager = socket.getfqdn()
    evtClass = "/Status/WinService"
    evtAgent = "zenwin"
    evtAlertGroup = "StatusTest"
    statmsg = "Windows Service '%s' is %s"


    def run(self, srec, zem):
        """Test a single device.
        """
        if not srec.svcs: return
        wql = "select Name from Win32_Service where State='Running'"
        svcs = [ svc.Name.lower() for svc in srec.query(wql) ]
        for name, (status, severity) in srec.svcs.items():
            evt = None
            log.debug("service: %s status: %d", name, status)
            if name.lower() not in svcs:
                srec.svcs[name] = status + 1, severity
                msg = self.statmsg % (name, "down")
                evt = self.mkevt(srec.name, name, msg, severity)
                log.info("svc down %s, %s", srec.name, name)
            elif status > 0:
                srec.svcs[name] = 0 , severity
                msg = self.statmsg % (name, "up")
                evt = self.mkevt(srec.name, name, msg, 0)
            if evt: zem.sendEvent(evt)

    
    def mkevt(self, devname, svcname, msg, sev=5):
        """Put event in the queue to be sent to the ZenEventManager.
        """
        evt = {}
        evt['device'] = devname
        evt['eventClass'] = self.evtClass
        evt['component'] = svcname
        evt['summary'] = msg
        evt['eventClass'] = self.evtClass
        evt['agent'] = self.evtAgent
        evt['severity'] = sev
        evt['eventGroup'] = self.evtAlertGroup
        evt['manager'] = self.manager
        if sev > 0: log.critical(msg)
        else: log.info(msg)
        return evt




