
import logging
log = logging.getLogger("zen.RRDUtil")

from Products.ZenModel.PerformanceConf import performancePath

class RRDUtil:
    def __init__(self, defaultRrdCreateCommand, defaultCycleTime):
        self.defaultRrdCreateCommand = defaultRrdCreateCommand
        self.defaultCycleTime = defaultCycleTime

    def save(self, path, value, rrdType, rrdCommand=None, cycleTime=None):
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
            dataSource = 'DS:%s:%s:%d:U:U' % ('ds0', rrdType,
                                              3*cycleTime)
            rrdtool.create(filename,
                           "--step",  str(cycleTime),
                           str(dataSource), *rrdCommand.split())
        
        if rrdType == 'COUNTER':
            value = long(value)
        try:
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            log.error('rrd error %s %s', err, path)

        if rrdType == 'COUNTER':
            startStop, names, values = \
                       rrdtool.fetch(filename, 'AVERAGE',
                                     '-s', 'now-%d' % cycleTime*2,
                                     '-e', 'now')
            value = values[0][0]
        return value

