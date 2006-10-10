#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenstep

Re-write an RRD files to have a different (larger) step.

$Id$
'''

import Globals
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenUtils.ZCmdBase import ZCmdBase

import os
import rrdtool
import logging
log = logging.getLogger('zen.updateStep')

DEFAULT='''RRA:AVERAGE:0.5:1:1800
RRA:AVERAGE:0.5:6:1800
RRA:AVERAGE:0.5:24:1800
RRA:AVERAGE:0.5:288:1800
RRA:MAX:0.5:288:1800'''.split()

def round(x):
    return int(x + 0.5)

class UpdateStep(ZCmdBase):
    """Run over the rrd files in a directory and write the data
    into updated config files"""

    def process(self, fullpath):
        log.debug("processing %s" % fullpath)
        newpath = os.path.join(os.path.dirname(fullname),
                               '.' + os.path.basename(file))
        # get type, old step?
        info = rrdtool.info(fullpath)
        type = info['ds']['ds0']['type']
        try:
            os.unlink(newpath)
        except OSError:
            pass
        data = rrdtool.fetch(fullpath, 'AVERAGE')
        (start, stop, step), source, points = data
        last = start
        rrdtool.create(
            newpath,
            'DS:ds0:%s:%d:U:U' % (type, 3*self.options.step),
            '--start', str(start - step),
            '--step', str(self.options.step),
            *defaultRRDCommand.split())

        rnd = lambda x: x
        if type == 'COUNTER':
            rnd = round
        for i, t in enumerate(range(start, stop, step)):
            p = points[i][0]
            if p is not None:
                rrdtool.update(newpath, '%d@%s' % (t, rnd(p)))
        if self.options.commit:
            os.rename(newpath, fullpath)

    def run(self):
        monitors = self.dmd.Monitors.Performance
        monitor = monitors._getOb(self.options.monitor)
        defaultRRDCommand = monitor.getDefaultRRDCreateCommand()
        for root, dirs, files in os.walk(self.options.root):
            for file in files:
                # skip workin files
                if file.startswith('.'): continue
                if not file.endswith('.rrd'): continue
                fullpath = os.path.join(root, file)
                process(fullpath)
                

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-s', '--step', dest='step', type='int',
                               default=300, help='Default step size in seconds')
        self.parser.add_option('-r', '--root', dest='root', 
                               default=performancePath(''),
                               help='Root tree to convert')
        self.parser.add_option('--commit', dest='commit', action='store_true',
                               default=False,
                               help='Really put the converted files in place.')
        self.parser.add_option('--monitor', dest='monitor', 
                               default='localhost',
                               help='Really put the converted files in place.')

if __name__ == '__main__':
    us = UpdateStep()
    us.run()

