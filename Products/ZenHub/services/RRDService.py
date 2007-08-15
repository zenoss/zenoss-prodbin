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

__doc__='''RRDService

Provides RRD services to zenhub clients.
'''

import os.path
from HubService import HubService
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.Thresholds import Thresholds
import time
import logging
log = logging.getLogger("zenhub")

class RRDService(HubService):


    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        # rrd is a dictionary of RRDUtil instances
        self.rrd = {}
        self.thresholds = Thresholds()


    def remote_writeRRD(self, devId, compType, compId, dpName, value):
        '''Write the given data to its rrd file.
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
        thresholds = [t for t in dp.datasource.rrdTemplate.thresholds()]
        thresholds = [t for t in thresholds if t.enabled]
        thresholds = [t for t in thresholds if dp.name() in t.dsnames]
        for t in thresholds:
            log.debug('Checking %s value of %s against threshold %s' %
                      (dp.name(), value, t.id))
            ti = t.createThresholdInstance(dev)
            self.thresholds.update(ti)
            for ev in self.thresholds.check(ti.context().fileKey(dp.name()),
                                            time.time(),
                                            value):
                self.zem.sendEvent(ev)
