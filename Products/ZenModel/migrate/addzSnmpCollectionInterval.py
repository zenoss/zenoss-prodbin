###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Add zSnmpCollectionInterval z property.  This replaces the per-collector
configuration property and allows for per-device collection intervals.

'''
import Migrate
import transaction

class addzSnmpCollectionInterval(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        if not hasattr( dmd.Devices, 'zSnmpCollectionInterval' ):
            localMonitor = dmd.Monitors.getPerformanceMonitor('localhost')
            collectorDefault = localMonitor.perfsnmpCycleInterval
            dmd.Devices._setProperty('zSnmpCollectionInterval',
                                     collectorDefault,
                                     'int')
            transaction.commit()

addzSnmpCollectionInterval()
