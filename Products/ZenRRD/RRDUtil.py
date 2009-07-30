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

__doc__ = """RRDUtil

Wrapper routines around the rrdtool library.
"""

import logging
log = logging.getLogger("zen.RRDUtil")

def _checkUndefined(x):
    """
    Sanity check on the min, max values

    @param x: RRD min or max value
    @type x: number
    @return: Either the number or 'U' (for undefined)
    @rtype: number or string
    """
    if x is None or x == '' or x == -1 or x == '-1':
        return 'U'
    return x


def convertToRRDTime(val):
    """
    Convert any value that is passed in to a string that is acceptable to use
    for RRDtool's start and end parameters. Raises ValueError if this is not
    possible.
    
    See the AT-STYLE TIME SPECIFICATION and TIME REFERENCE SPECIFICATION
    sections of the following document.
    
        http://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html
    
    Note: Currently this method is only fixing floats by turning them into
          strings with no decimal places.
    """
    # Integers are ok. This will also strip decimal precision.
    try:
        result = int(val)
        return str(result)
    except ValueError:
        pass

    return str(val)


class RRDUtil:
    """
    Wrapper class around rrdtool
    """

    def __init__(self, defaultRrdCreateCommand, defaultCycleTime):
        """
        Initializer

        The RRD creation command is only used if the RRD file doesn't
        exist and no rrdCommand was specified with the save() method.

        @param defaultRrdCreateCommand: RRD creation command
        @type defaultRrdCreateCommand: string
        @param defaultCycleTime: expected time to periodically collect data
        @type defaultCycleTime: integer
        """
        self.defaultRrdCreateCommand = defaultRrdCreateCommand
        self.defaultCycleTime = defaultCycleTime
        self.dataPoints = 0
        self.cycleDataPoints = 0


    def endCycle(self):
        """
        Report on the number of data points collected in a cycle,
        and reset the counter for a new cycle.

        @return: number of data points collected during the cycle
        @rtype: number
        """
        result = self.cycleDataPoints
        self.cycleDataPoints = 0
        return result


    def performancePath(self, path):
        """
        Given a path, return its location from $ZENHOME and the
        perf/ directories.

        @param path: name for a datapoint in a path (eg device/component/datasource_datapoint)
        @type path: string
        @return: absolute path
        @rtype: string
        """
        from Products.ZenModel.PerformanceConf import performancePath
        return performancePath(path)


    def save(self, path, value, rrdType, rrdCommand=None, cycleTime=None,
             min='U', max='U'):
        """
        Save the value provided in the command to the RRD file specified in path.

        If the RRD file does not exist, use the rrdType, rrdCommand, min and
        max parameters to create the file.

        @param path: name for a datapoint in a path (eg device/component/datasource_datapoint)
        @type path: string
        @param value: value to store into the RRD file
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        @param rrdCommand: RRD file creation command
        @type rrdCommand: string
        @param cycleTime: length of a cycle
        @type cycleTime: number
        @param min: minimum value acceptable for this metric
        @type min: number
        @param max: maximum value acceptable for this metric
        @type max: number
        @return: the parameter value converted to a number
        @rtype: number or None
        """
        import rrdtool, os

        if value is None: return None

        self.dataPoints += 1
        self.cycleDataPoints += 1

        if cycleTime is None:
            cycleTime = self.defaultCycleTime

        filename = self.performancePath(path) + '.rrd'
        if not rrdCommand:
            rrdCommand = self.defaultRrdCreateCommand
        if not os.path.exists(filename):
            log.debug("Creating new RRD file %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname, 0750)

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
        else:
            value = float(value)
        try:
            rrdtool.update(filename, 'N:%s' % value)
            log.debug('%s: %r', filename, value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            log.error('rrdtool reported error %s %s', err, path)

        if rrdType in ('COUNTER', 'DERIVE'):
            startStop, names, values = \
                rrdtool.fetch(filename, 'AVERAGE',
                    '-s', 'now-%d' % (cycleTime*2),
                    '-e', 'now')
            values = [ v[0] for v in values if v[0] is not None ]
            if values: value = values[-1]
            else: value = None
        return value
