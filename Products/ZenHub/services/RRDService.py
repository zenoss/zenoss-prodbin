#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''RRDService

Provides RRD services to zenhub clients.
'''

from HubService import HubService
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.ThresholdManager import ThresholdManager, Threshold


class RRDService(HubService):


    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        # rrd is a dictionary of RRDUtil instances
        self.rrd = {}
        # counts is a dictionary of integers tracking how many times
        # each threshold has been exceeded sequentially.
        self.counts = {}
        
    
    def remote_writeRRD(self, devId, compType, compId, dpName, value):
        ''' Write the given data to it's rrd file.
        Also check any thresholds and send events if value is out of bounds.
        '''
        dev = self.getDeviceOrComponent(devId, compType, compId)
        dp = d.getDataPoint(dpName)
        rrdKey = (dev.getPrimaryPath(), dp.getPrimaryPath())
        if self.rrd.has_key(key):
            rrd = self.rrd[rrdKey]
        else:
            rrd = self.rrd.setdefault(rrdKey,
                    RRDUtil(dp.createCmd or self.getDefaultRRDCreateCommand(),
                            dp.datasource.cycletime))        
        value = rrd.save(os.path.join(dev.rrdPath(), dp.name),
                        value, 
                        dp.rrdtype, 
                        dp.createCmd or self.getDefaultRRDCreateCommand(), 
                        dp.datasource.cycleTime,
                        dp.rrdmin,
                        dp.rrdmax)
        self.checkThresholds(dev, dp, value)
        return value


    def getDefaultRRDCreateCommand(self):
        ''' Return the rrd create command to be used if a datapoint doesn't
        explicitly give one.
        '''
        raise 'Not Implemented'


    def getDeviceOrComponent(deviceId, compId, compType):
        ''' If a compId is given then try to return that component.  If unable
        to find it or if compId is not specified then try to return the
        given device.  If unable to find then return None.
        '''
        d = None
        device = self.dmd.Devices.findDevice(deviceId)
        if device:
            if componentId:
                for component in device.getDeviceComponents():
                    if component.meta_type == componentType \
                            and component.id == componentId:
                        d = component
                        break
            else:
                d = device
        return d
        

    def checkThresholds(self, dev, dp, value):
        ''' Check the given value against any thresholds.  Count the number of
        times a dp has exceeded a given threshold in self.counts.  Send events
        as appropriate.
        '''
        if value is None:
            return
        # Loop through the enabled thresholds on the template containing
        # this datapoint.
        for t in [t for t in dp.datasource.rrdTemplate.thresholds()
                    if t.enabled and dp.name() in t.dsnames()]:
            countKey = (dev.getPrimaryPath(), dp.getPrimaryPath(), t.id)
            count = self.status.setdefault(countKey, 0)
            limit = None
            how = None
            maxv = t.getMaxval(dev)
            if maxv is not None and value > maxv:
                limit = maxv
                how = 'exceeded'
            else:
                minv = t.getMinval(dev)
                if minv is not None and value < minv:
                    limit = minv
                    how = 'not met'
            # Only need to take action if threshold was exceeded or if it was
            # previously exceeded.
            if how or count:
                if dev.meta_type == 'Device':
                    devId = dev.id
                    compId = ''
                else:
                    devId = dev.device().id
                    compId = dev.id
                if how:
                    self.counts[countKey] += 1
                    severity = t.severity
                    if t.escalateCount and count >= t.escalateCount:
                        severity += 1
                    summary = ('%s %s threshold of %s %s:' %
                                (devId, dp.name(), limit, how) +
                                ' current value %.2f' % float(value))
                else:
                    self.counts[countKey] = 0
                    severity = 0
                    summary = ('%s %s threshold restored' %
                                (devId, dp.name()) +
                                ' current value: %.2f' % float(value))
                self.zenm.sendEvent(
                                device=devId,
                                summary=summary,
                                eventClass=t.eventClass,
                                eventKey=dp.name(),
                                component=compId,
                                severity=severity)




