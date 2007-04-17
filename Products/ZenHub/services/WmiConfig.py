#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''WmiService

Provides Wmi config to zenwin clients.
'''

from twisted.spread import pb
class ZenWinConfig(pb.Copyable, pb.RemoteCopy):

    def __init__(self, monitor, devices):
        self.monitor = monitor
        self.devices = devices
pb.setUnjellyableForClass(ZenWinConfig, ZenWinConfig)

from Products.ZenHub.HubService import HubService
class WmiConfig(HubService):
    
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)

    def getDeviceWinInfo(self):
        """Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """
        devinfo = []
        for dev in self.config.device():
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            sev = getattr(dev, 'zWinEventlogMinSeverity', '')
            devinfo.append((dev.id,user,passwd,sev,dev.absolute_url()))
        return devinfo
    
    
    def getWinServices(self):
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
        return ZenWinConfig(self.config.propertyItems(),
                            self.getWinServices())
