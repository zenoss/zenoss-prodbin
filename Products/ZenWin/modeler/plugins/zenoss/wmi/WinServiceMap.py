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

from Products.ZenWin.WMIPlugin import WMIPlugin
from Products.ZenUtils.Utils import prepId
from Products.ZenEvents.ZenEventClasses import Status_WinService
from socket import getfqdn

EVENTS = "Events"
STATMSG = "Windows Service '%s' is %s"

class WinServiceMap(WMIPlugin):

    maptype = "WinServiceMap"
    compname = "os"
    relname = "winservices"
    modname = "Products.ZenModel.WinService"
    
    attrs = ("acceptPause","acceptStop","name","caption",
             "pathName","serviceType","startMode","startName","state")
    
    def queries(self):
        return {
     "Win32_Service":"Select %s From Win32_Service" % \
        (",".join(self.attrs)),
    }
    
    def getEvents(self, device, results, log):
        runningServices = []
        for svc in results["Win32_Service"]:
            if svc.state == "Running":
                runningServices.append(svc.name)
        # BUILD EVENT LIST TO SEND
        events = []
        for name, (status, severity) in device.services.items():
            if name in runningServices:
                log.info('%s: %s running' % (device.id, name)) 
                device.services[name] = 0, severity
                if status != 0:
                    msg = STATMSG % (name, "up")
                    events.append(dict(summary=msg,
                        eventClass=Status_WinService,
                        device=device.id,
                        severity=0,
                        agent="zenwinmodeler",
                        component=name,
                        eventGroup= "StatusTest",
                        manager=getfqdn())) 
                    log.info("svc up %s, %s", device.id, name) 
            else:
                log.warning('%s: %s stopped' % (device.id, name))
                device.services[name] = status + 1, severity
                msg = STATMSG % (name, "down")
                log.critical(msg)
                events.append(dict(summary=msg,
                    eventClass=Status_WinService,
                    device=device.id,
                    severity=severity,
                    agent="zenwinmodeler",
                    component=name,
                    eventGroup= "StatusTest",
                    manager=getfqdn()))
                log.info("svc down %s, %s", device.id, name) 
        return events
        
    def process(self, device, results, log):
        """
        Collect win service info from this device.
        """
        log.info('Processing WinServices for device %s' % device.id)
        
        rm = self.relMap()
        for svc in results["Win32_Service"]:
            om = self.objectMap()
            om.id = prepId(svc.name)
            om.setServiceClass = {'name':svc.name, 'description':svc.caption}
            for att in self.attrs:
                if att in ("name", "caption", "state"): continue
                setattr(om, att, getattr(svc, att, "")) 
            rm.append(om)
        
        return rm

