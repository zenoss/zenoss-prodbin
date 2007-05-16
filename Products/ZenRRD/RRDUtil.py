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

import logging
log = logging.getLogger("zen.RRDUtil")

from Products.ZenModel.PerformanceConf import performancePath

def _checkUndefined(x):
    if x is None or x == '' or x == -1 or x == '-1':
        return 'U'
    return x

class RRDUtil:
    def __init__(self, defaultRrdCreateCommand, defaultCycleTime):
        self.defaultRrdCreateCommand = defaultRrdCreateCommand
        self.defaultCycleTime = defaultCycleTime

    def save(self, path, value, rrdType, rrdCommand=None, cycleTime=None,
             min='U', max='U'):
        import rrdtool, os

        if cycleTime is None:
            cycleTime = self.defaultCycleTime

        filename = performancePath(path) + '.rrd'
        if not rrdCommand:
            rrdCommand = self.defaultRrdCreateCommand
        if not os.path.exists(filename):
            log.debug("create new rrd %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            min, max = map(_checkUndefined, (min, max))
            dataSource = 'DS:%s:%s:%d:%s:%s' % ('ds0', rrdType,
                                                3*cycleTime, min, max)
            rrdtool.create(filename,
                           "--step",  str(cycleTime),
                           str(dataSource), *rrdCommand.split())
        
        if rrdType in ('COUNTER', 'DERIVE'):
            try:
                value = long(value)
            except (TypeError, ValueError):
                return None
        try:
            rrdtool.update(filename, 'N:%s' % value)
            log.debug('%s: %r', filename, value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            log.error('rrd error %s %s', err, path)

        if rrdType in ('COUNTER', 'DERIVE'):
            startStop, names, values = \
                       rrdtool.fetch(filename, 'AVERAGE',
                                     '-s', 'now-%d' % (cycleTime*2),
                                     '-e', 'now')
            value = values[0][0]
        return value

