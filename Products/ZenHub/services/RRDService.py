#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''RRDService

Provides RRD services to zenhub clients.
'''

import os.path
from HubService import HubService
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.ThresholdManager import ThresholdManager, Threshold
import logging
log = logging.getLogger("zenhub")


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
        log.debug('Writing %s %s' % (dpName, value))
        dev = self.getDeviceOrComponent(devId, compType, compId)
        dp = dev.getRRDDataPoint(dpName)
        if not dp:
            log.warn('Did not find datapoint %s on device %s', dpName, devId)
            return None
        rrdKey = (dev.getPrimaryPath(), dp.getPrimaryPath())
        rrdCreateCmd = dp.createCmd or self.getDefaultRRDCreateCommand(dev)
        if self.rrd.has_key(rrdKey):
            rrd = self.rrd[rrdKey]
        else:
            rrd = RRDUtil(rrdCreateCmd, dp.datasource.cycletime)
            self.rrd[rrdKey] = rrd
        value = rrd.save(os.path.join(dev.rrdPath(), dp.name()),
                        value, 
                        dp.rrdtype,
                        rrdCreateCmd,
                        dp.datasource.cycletime,
                        dp.rrdmin,
                        dp.rrdmax)
        self.checkThresholds(dev, dp, value)
        return value


    def getDefaultRRDCreateCommand(self, device):
        return device.perfServer().getDefaultRRDCreateCommand()
        

    def getDeviceOrComponent(self, devId, compId, compType):
        ''' If a compId is given then try to return that component.  If unable
        to find it or if compId is not specified then try to return the
        given device.  If unable to find then return None.
        '''
        d = None
        device = self.dmd.Devices.findDevice(devId)
        if device:
            if compId:
                for comp in device.getDeviceComponents():
                    if comp.meta_type == compType and comp.id == compId:
                        d = comp
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
                    if t.enabled and dp.name() in t.dsnames]:
            log.debug('Checking %s value of %s against threshold %s: %s:%s' %
                (dp.name(), value, t.id, t.getMinval(dev), t.getMaxval(dev)))
            countKey = (dev.getPrimaryPath(), dp.getPrimaryPath(), t.id)
            count = self.counts.setdefault(countKey, 0)
            limit = None
            how = None
            maxv = t.getMaxval(dev)
            if maxv is not None and value > maxv:
                log.debug('threshold exceeded')
                limit = maxv
                how = 'exceeded'
            else:
                minv = t.getMinval(dev)
                if minv is not None and value < minv:
                    log.debug('threshold not met')
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
                self.zem.sendEvent(dict(
                                device=devId,
                                summary=summary,
                                eventClass=t.eventClass,
                                eventKey=dp.name(),
                                component=compId,
                                severity=severity))




