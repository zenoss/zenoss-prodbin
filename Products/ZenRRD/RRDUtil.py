
import logging
log = logging.getLogger("zen.RRDUtil")

from Products.ZenModel.PerformanceConf import performancePath

class RRDUtil:
    def __init__(self, defaultRrdCreateCommand, cycleTime):
        self.defaultRrdCreateCommand = defaultRrdCreateCommand
        self.cycleTime = cycleTime

    def save(self, path, value, rrdType, rrdCommand = None):
        import rrdtool, os
        filename = performancePath(path) + '.rrd'
        if not rrdCommand:
            rrdCommand = self.defaultRrdCreateCommand
        if not os.path.exists(filename):
            log.debug("create new rrd %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            dataSource = 'DS:%s:%s:%d:U:U' % ('ds0', rrdType,
                                              3*self.cycleTime)
            rrdtool.create(filename,
                           "--step",  str(self.cycleTime),
                           str(dataSource), *rrdCommand.split())
        
        try:
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            log.error('rrd error %s %s', err, path)

        if rrdType == 'COUNTER':
            startStop, names, values = \
                       rrdtool.fetch(filename, 'AVERAGE',
                                     '-s', 'now-%d' % self.cycleTime*2,
                                     '-e', 'now')
            value = values[0][0]
        return value

