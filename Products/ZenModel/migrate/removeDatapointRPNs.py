###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Remove RPN formulas from datapoint objects (they now reside in the GraphDataPoint
objects)

'''

import Migrate
from Products.ZenModel.RRDTemplate import YieldAllRRDTemplates
import logging
log = logging.getLogger("zen.migrate")

class RemoveDataPointRPNs(Migrate.Step):
    version = Migrate.Version(2, 2, 4)

    def cutover(self, dmd):
        ''' Find all the non-empty RPNs and empty them
        '''
        templates=YieldAllRRDTemplates( dmd.Devices )
        for template in templates:
            for datasource in template.datasources.objectValues():
                for datapoint in datasource.datapoints.objectValues():
                    if len( datapoint.rpn ) > 0:
                        log.debug( "Resetting rpn for %s.%s.%s from %s" % \
                                (template.id, datasource.id, \
                                 datapoint.id,datapoint.rpn) )
                        datapoint.rpn=''

RemoveDataPointRPNs()
