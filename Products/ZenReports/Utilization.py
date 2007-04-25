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
from Products.ZenUtils import Time

def getSummaryArgs(dmd, args):
    zem = dmd.ZenEventManager
    startDate = args.get('startDate', zem.defaultAvailabilityStart())
    endDate = args.get('endDate', zem.defaultAvailabilityEnd())
    startDate, endDate = map(Time.ParseUSDate, (startDate, endDate))
    startDate = min(startDate, endDate - 1)
    how = args.get('how', 'AVERAGE')
    return dict(start=startDate, end=endDate, function=how)

def reversedSummary(summary):
    swapper = { 'MAXIMUM':'MINIMUM', 'MINIMUM':'MAXIMUM'}
    summary = summary.copy()
    current = summary['function']
    summary['function'] = swapper.get(current, current)
    return summary


