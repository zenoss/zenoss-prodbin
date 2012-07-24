##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''zenstep

Re-write an RRD files to have a different (larger) step.

$Id$
'''

import Globals
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenUtils.ZCmdBase import ZCmdBase

import os
from itertools import *
import rrdtool
import logging
log = logging.getLogger('zen.updateStep')

class UpdateStep(ZCmdBase):
    """Run over the rrd files in a directory and write the data
    into updated config files"""

    def processRRA(self, fullpath, rra, info, dump):
        "process one archive in the file"
        step = info['step']
        end = info['last_update']
        pdp_per_row = rra['pdp_per_row']
        rows = rra['rows']
        resolution = step*pdp_per_row
        start = end - resolution*rows
        start = start/resolution*resolution
        end = end/resolution*resolution
        data = rrdtool.fetch(fullpath,
                             'AVERAGE',
                             '--resolution', str(resolution),
                             '--start', str(start),
                             '--end', str(end))
        (start, end, resolution), unused, data = data
        rnd = lambda x: x
        if info['ds[ds0].type'] == 'COUNTER':
            rnd = lambda x: int(x+0.5)
        result = []
        for i, (v,) in enumerate(data):
            if v != None:
                dump[start + i*resolution] = rnd(v)
        return result
                

    def process(self, fullpath):
        "convert a single file"
        log.debug("processing %s" % fullpath)
        newpath = os.path.join(os.path.dirname(fullpath),
                               '.' + os.path.basename(fullpath))
        # get type, old step
        info = rrdtool.info(fullpath)
        dataType = info['ds[ds0].type']

        try:
            os.unlink(newpath)
        except OSError:
            pass

        rraList = []
        for rraIndex in count():
            rra = {}
            rra['pdp_per_row'] = info.get('rra[%s].pdp_per_row' % rraIndex)
            rra['rows'] = info.get('rra[%s].rows' % rraIndex)
            if rra['pdp_per_row'] is None or rra['rows'] is None:
                break
            rraList.append(rra)

        # Collect some information about the current file:
        # how far back can the data go?
        earliest = info['last_update']

        # how wide is the biggest data point?
        biggest = 0
            
        for rra in rraList:
            size = rra['pdp_per_row'] * info['step']
            earliest = min(earliest, info['last_update'] - rra['rows'] * size)
            biggest = max(biggest, size)
            
        # create a file with the correct step to accept the data
        rrdtool.create(
            newpath,
            'DS:ds0:%s:%d:U:U' % (dataType, biggest * 2),
            '--start', str(earliest),
            '--step', str(self.options.step),
            *self.defaultRRDCommand.split())
            
        # extract the time and values from each archive
        updates = {}
        
        for rra in rraList:            
            self.processRRA(fullpath, rra, info, updates)
            
        # get the times in order
        updates = updates.items()
        updates.sort()
        rrdtool.update(newpath, *[('%d@%s' % (t, v)) for t, v in updates])
        # use a reasonable heartbeat
        rrdtool.tune(newpath, '-h','ds0:%d' % (self.options.step*3))
        if self.options.commit:
            os.rename(newpath, fullpath)


    def run(self):
        monitors = self.dmd.Monitors.Performance
        monitor = monitors._getOb(self.options.monitor)
        self.defaultRRDCommand = monitor.getDefaultRRDCreateCommand()
        if self.options.filename:
            self.process(self.options.filename)
        else:
            for root, dirs, files in os.walk(self.options.root):
                for filename in files:
                    # skip working files
                    if filename.startswith('.'): continue
                    if not filename.endswith('.rrd'): continue
                    fullpath = os.path.join(root, filename)
                    self.process(fullpath)
                

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-s', '--step', dest='step', type='int',
                               default=300, help='Default step size in seconds')
        self.parser.add_option('-r', '--root', dest='root', 
                               default=performancePath(''),
                               help='Root tree to convert')
        self.parser.add_option('-f', '--file', dest='filename', 
                               help='Root tree to convert')
        self.parser.add_option('--commit', dest='commit', action='store_true',
                               default=False,
                               help='Really put the converted files in place.')
        self.parser.add_option('--monitor', dest='monitor', 
                               default='localhost',
                               help='Name of this collection host.')

if __name__ == '__main__':
    us = UpdateStep()
    us.run()
