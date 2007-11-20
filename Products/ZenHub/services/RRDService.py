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
from Products.ZenRRD.Thresholds import Thresholds
from RRDImpl import RRDImpl
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

        

