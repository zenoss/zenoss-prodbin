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

from HubService import HubService
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.Thresholds import Thresholds
from RRDImpl import RRDImpl
import time
import logging
log = logging.getLogger("zenhub")

class RRDService(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)

        # rrd is a dictionary of RRDUtil instances
        self.rrd = {}
        self.thresholds = Thresholds()
        self.rrdimpl = RRDImpl(dmd)


    def remote_writeRRD(self, devId, compType, compId, dpName, value):
        '''Write the given data to its rrd file.
        Also check any thresholds and send events if value is out of bounds.
        '''

        return self.rrdimpl.writeRRD(devId, compType, compId, dpName, value)


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
        

