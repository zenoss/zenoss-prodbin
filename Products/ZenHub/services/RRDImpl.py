##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """RRDImpl

Implementation of basic RRD services for zenhub
"""

import os.path
import logging
import time

from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenEvents.ZenEventClasses import Critical, Status_Perf


log = logging.getLogger("zenhub")



class RRDImpl(object):
    """
    RRDUtil wrapper class for zenhub
    """

    # list of RRD types that only accept long or integer values (no floats!)
    LONG_RRD_TYPES = ['COUNTER', 'DERIVE']

    def __init__(self, dmd):
        """
        Initializer

        @param dmd: Device Management Database (DMD) reference
        @type dmd: dmd object
        """
        # RRD is a dictionary of RRDUtil instances, keyed by (device,datapoint) tuples
        self.rrd = {}
        # counts is a dictionary of integers tracking how many times
        # each threshold has been exceeded sequentially.
        self.counts = {}

        self.dmd = dmd
        self.zem = dmd.ZenEventManager


    def writeRRD(self, devId, compType, compId, dpName, value):
        """
        Write the given data to its RRD file.
        Also check any thresholds and send events if value is out of bounds.
        Note that if the write does not succeed, a None value is returned.

        @param devId: device name (as known by DMD)
        @type devId: string
        @param compType: component type (found in objects meta_type field)
        @type compType: string
        @param compId:  name of the component
        @type compId: string
        @param dpName: name of the data point
        @type dpName: string
        @param value: performance metric to store
        @type value: number
        @return: valid value (ie long or float) or None
        @rtype: number or None
        """
        log.debug('Writing %s %s' % (dpName, value))
        dev = self.getDeviceOrComponent(devId, compType, compId)
        dp = dev.getRRDDataPoint(dpName)
        if not dp:
            log.warn('Did not find datapoint %s on device %s', dpName, devId)
            return None
        rrdKey = (dev.getPrimaryPath(), dp.getPrimaryPath())
        rrdCreateCmd = None
        if rrdKey in self.rrd:
            rrd = self.rrd[rrdKey]
        else:
            rrdCreateCmd = dp.createCmd or self.getDefaultRRDCreateCommand(dev)
            rrd = RRDUtil(rrdCreateCmd, dp.datasource.cycletime)
            self.rrd[rrdKey] = rrd

        # convert value to a long if our data point uses a long type
        if dp.rrdtype in RRDImpl.LONG_RRD_TYPES:
            try:
                value = long(value)
            except ValueError:
                log.warn("Value '%s' received for data point '%s' that " \
                         "could not be converted to a long" % \
                         (value, dp.rrdtype))

        # see if there are any thresholds defined for this datapoint, so we can
        # choose a more optimal RRD storage method if there aren't any
        dp_has_threshold = self.hasThreshold(dp)
        if dp_has_threshold:
            rrd_write_fn = rrd.save
        else:
            rrd_write_fn = rrd.put
            
        path = os.path.join(dev.rrdPath(), dp.name())
        try:
            value = rrd_write_fn( path,
                        value, 
                        dp.rrdtype,
                        rrdCreateCmd,
                        dp.datasource.cycletime,
                        dp.rrdmin,
                        dp.rrdmax)

        except Exception, ex:
            summary= "Unable to save data in zenhub for RRD %s" % \
                              path
            log.critical( summary )

            message= "Data was value= %s, type=%s, min=%s, max=%s" % \
                     ( value, dp.rrdtype, dp.rrdmin, dp.rrdmax, )
            log.critical( message )
            log.exception( ex )

            import traceback
            trace_info= traceback.format_exc()

            evid= self.zem.sendEvent(dict(
                dedupid="%s|%s" % (devId, 'RRD write failure'),
                severity=Critical,
                device=devId,
                eventClass=Status_Perf,
                component="RRD",
                compType=compType,
                compId=compId,
                datapoint=dpName,
                message=message,
                traceback=trace_info,
                summary=summary))

            # Skip thresholds
            return

        if dp_has_threshold:
            self.checkThresholds(dev, dp, value)
        return value


    def getDefaultRRDCreateCommand(self, device):
        """
        Get the overridable create command for new RRD files.

        @param device: device object from in DMD
        @type device: device object
        @return: RRD create command
        @rtype: string
        """
        return device.perfServer().getDefaultRRDCreateCommand()
        

    def getDeviceOrComponent(self, devId, compId, compType):
        """
        If a compId is given then try to return that component.  If unable
        to find it or if compId is not specified then try to return the
        given device.  If unable to find then return None.

        @param devId: device name (as known by DMD)
        @type devId: string
        @param compId:  name of the component
        @type compId: string
        @param compType: component type (found in objects meta_type field)
        @type compType: string
        @return: device or component object
        @rtype: object
        """
        retobj = None
        device = self.dmd.Devices.findDevice(devId)
        if device:
            if compId:
                retobj = next((comp for comp in device.getDeviceComponents() 
                                if comp.meta_type == compType and comp.id == compId), 
                            None)

            else:
                retobj = device
        return retobj
    
    def hasThreshold(self, dp):
        dp_name = dp.name()
        return any(thresh.enabled and dp_name in thresh.dsnames 
                    for thresh in dp.datasource.rrdTemplate.thresholds())

    def checkThresholds(self, dev, dp, value):
        """
        Check the given value against any thresholds.  Count the number of
        times a dp has exceeded a given threshold in self.counts.  Send events
        as appropriate.

        @param dev: device or component object
        @type dev: object
        @param dp: datapoint
        @type dp: RRD datapoint object
        @param value: performance metric to compare
        @type value: number
        """
        if value is None:
            return

        # Loop through the enabled thresholds on the template containing
        # this datapoint.
        dp_name = dp.name()
        for t in [t for t in dp.datasource.rrdTemplate.thresholds()
                  if t.enabled and dp_name in t.dsnames]:
            log.debug('Checking %s value of %s against threshold %s: %s:%s' %
                (dp_name, value, t.id, t.getMinval(dev), t.getMaxval(dev)))
            inst = t.createThresholdInstance(dev)
            # storing the count external to the instances is a little
            # broken, but I don't want to cache the instances
            countKey = inst.countKey('dp_ds')
            inst.count[countKey] = self.counts.get(countKey, None)
            for evt in inst.checkRaw(dp.name(), time.time(), value):
                self.zem.sendEvent(evt)
            self.counts[countKey] = inst.countKey('dp_ds')
