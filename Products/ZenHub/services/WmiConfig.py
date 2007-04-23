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

__doc__='''WmiService

Provides Wmi config to zenwin clients.
'''

from Products.ZenHub.HubService import HubService
from Products.DataCollector.ApplyDataMap import ApplyDataMap

class WmiConfig(HubService):
    
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)

    def remote_getDeviceWinInfo(self):
        """Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """
        devinfo = []
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            sev = getattr(dev, 'zWinEventlogMinSeverity', '')
            devinfo.append((dev.id,user,passwd,sev,dev.absolute_url()))
        return devinfo
    
    
    def remote_getWinServices(self):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        svcinfo = []
        allsvcs = {}
        for s in self.dmd.Devices.getSubComponents("WinService"):
            svcs=allsvcs.setdefault(s.hostname(),{})
            name = s.name()
            if type(name) == type(u''):
                name = name.encode(s.zCollectorDecoding)
            svcs[name] = (s.getStatus(), s.getAqProperty('zFailSeverity'))
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            svcs = allsvcs.get(dev.getId(), {})
            if not svcs and not dev.zWinEventlog: continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            svcinfo.append((dev.id, user, passwd, svcs))
        return svcinfo

    def remote_getConfig(self):
        return self.config.propertyItems()

    def remote_applyDataMap(self,
                            url,
                            datamap,
                            relname="",
                            compname="",
                            modname=""):
        dev = self.dmd.getObjByPath(url)
        adm = ApplyDataMap()
        result = adm.applyDataMap(dev,
                                  datamap,
                                  relname=relname,
                                  compname=compname,
                                  modname=modname)
        import transaction
        transaction.commit()
        return result
        
