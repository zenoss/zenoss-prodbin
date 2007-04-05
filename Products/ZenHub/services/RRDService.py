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

class RRDService(HubService):


    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.rrd = {}


    def remote_writeRRD(self, path, value, rrdType, rrdCmd, cycleTime=None,
                        minv='U', maxv='U'):
        if self.rrd.has_key(path):
            rrd = self.rrd[path]
        else:
            rrd = RRDUtil(rrdCmd, cycleTime)
            self.rrd[path] = rrd
        value = rrd.save(path, value, rrdType, rrdCmd, cycleTime, minv, maxv)
        return value
