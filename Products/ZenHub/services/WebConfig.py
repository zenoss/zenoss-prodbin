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


    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.monitor = self.dmd.Monitors.Performance._getOb(self.instance)


    def remote_getPageChecks(self):
        pageChecks = []
        for dev in self.monitor.devices():
            dev = dev.primaryAq()
            pageChecks += self.getDevicePageChecks(dev)
        return pageChecks
                
        
    def remote_getPageCheckUpdates(self):
        return self.remote_getPageChecks()


    def remote_getDefaultRRDCreateCommand(self):
        return self.monitor.getDefaultRRDCreateCommand()


    def getDevicePageChecks(self, dev):
        result = []
        if not dev.monitorDevice():
            return result
        for templ in dev.getRRDTemplates():
            threshs = dev.getThresholds(templ)
            dataSources = templ.getRRDDataSources('PAGECHECK')
            for ds in dataSources:
                if not ds.enabled: continue
                points = [{'id': dp.id, 
                            'path': '/'.join((dev.rrdPath(), dp.name())),
                            'rrdType': dp.rrdtype,
                            'rrdCmd': dp.createCmd,
                            'minv': dp.rrdmin,
                            'maxv': dp.rrdmax,
                            'thesholds': threshs.get(dp.name(), []),
                            }
                            for dp in ds.getRRDDataPoints()]
                key = ds.eventKey or ds.id
                result.append({
                                'device': dev.id,
                                'manageIp': dev.manageIp,
                                'timeout': dev.zCommandCommandTimeout,
                                'datasource': ds.id or '',
                                'datapoints': points or (),
                                'defaultRrdCmd': 
                                    self.monitor.getDefaultRRDCreateCommand(),
                                'cycletime': ds.cycletime or '',
                                'component': ds.component or '',
                                'eventClass': ds.eventClass or '',
                                'eventKey': key or '',
                                'severity': ds.severity or '',
                                'userAgent': ds.userAgent or '',
                                'recording': ds.recording or '',
                                'initialUrl': ds.initialURL or '',
                                'command': ds.getCommand(dev) or '',
                                'commandHash': ds.commandHash or '',
                                })
        return result


