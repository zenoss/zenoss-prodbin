##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"Change the old default of rrdmax from -1 to None"

import Migrate

def _cutoverTemplate(template):
    for s in template.datasources():
        for p in s.datapoints():
            if p.rrdmax == -1:
                p.rrdmax = None

def _convertFile(filename):
    import rrdtool
    try:
        if rrdtool.info(filename)['ds[ds0].type'] == 'COUNTER':
            rrdtool.tune(filename,
                         '-d', 'ds0:DERIVE',
                         '-i', 'ds0:0')
    except KeyError:
        pass
    

class RRDMinValue2(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        import os
        from Products.ZenModel.PerformanceConf import PERF_ROOT

        # get all the templates
        for org in dmd.Devices.getSubOrganizers():
            map(_cutoverTemplate, org.getRRDTemplates())
        # get all the device-specific templates
        for dev in dmd.Devices.getSubDevices():
            map(_cutoverTemplate, dev.getRRDTemplates())

        for d, _, files in os.walk(PERF_ROOT):
            for f in files:
                if f.endswith('.rrd'):
                    _convertFile(os.path.join(d, f))

RRDMinValue2()
