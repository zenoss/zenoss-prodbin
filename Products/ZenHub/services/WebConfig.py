#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''WebConfig

ZenHub service for handling zenweb configuration
'''

from HubService import HubService

class WebConfig(HubService):


    def monitor(self):
        return self.dmd.Monitors.Performance._getOb(self.instance)


    def remote_getPageChecks(self):
        pageChecks = []
        for dev in self.monitor().devices():
            pageChecks += self.getDevicePageChecks(dev)
        return pageChecks
                
        
    def remote_getPageCheckUpdates(self):
        return self.remote_getPageChecks()


    def remote_getDefaultRRDCreateCommand(self):
        return self.monitor().getDefaultRRDCreateCommand()


    def getDevicePageChecks(self, dev):
        result = []
        if not dev.monitorDevice():
            return result
        for templ in dev.getRRDTemplates():
            threshs = self.getThresholds(templ)
            dataSources = templ.getRRDDataSources('PAGECHECK')
            for ds in dataSources:
                if not ds.enabled: continue
                points = [(dp.id, 
                            '/'.join((dev.rrdPath, dp.name())),
                            dp.rrdtype,
                            dp.createCmd,
                            (dp.rrdmin, dp.rrdmax),
                            threshs.get(dp.name(), []))
                            for dp in ds.getRRDDataPoints]
                key = ds.eventKey or ds.id
                result.append({
                                'device': dev.id,
                                'manageIp': dev.manageIp,
                                'timeout': dev.zCommandCommandTimeout,
                                'datasource': ds.id or '',
                                'datapoints': points or (),
                                'cycletime': ds.cycletime or '',
                                'component': ds.component or '',
                                'eventClass': ds.eventClass or '',
                                'eventKey': key or '',
                                'severity': ds.severity or '',
                                'userAgent': ds.userAgent or '',
                                'recording': ds.recording or '',
                                'initialUrl': ds.initialURL or '',
                                'command': ds.getCommand(self) or '',
                                'commandHash': ds.commandHash or '',
                                })
        return result


