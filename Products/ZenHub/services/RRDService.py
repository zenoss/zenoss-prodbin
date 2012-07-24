##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''RRDService

Provides RRD services to zenhub clients.
'''

from HubService import HubService
from Products.ZenRRD.Thresholds import Thresholds
from RRDImpl import RRDImpl
import logging
log = logging.getLogger("zenhub")
from Products.ZenHub.PBDaemon import translateError

class RRDService(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)

        # rrd is a dictionary of RRDUtil instances
        self.rrd = {}
        self.thresholds = Thresholds()
        self.rrdimpl = RRDImpl(dmd)


    @translateError
    def remote_writeRRD(self, devId, compType, compId, dpName, value):
        '''Write the given data to its rrd file.
        Also check any thresholds and send events if value is out of bounds.
        '''

        return self.rrdimpl.writeRRD(devId, compType, compId, dpName, value)
