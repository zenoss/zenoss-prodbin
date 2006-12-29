__doc__='''

Convert cpu tracking to DERIVE rrd type

'''

import Migrate


class RRDCpuType(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        import os
        import rrdtool
        from Products.ZenModel.PerformanceConf import PERF_ROOT
        CPU = 'cpu_cpu.rrd'

        for d, _, files in os.walk(PERF_ROOT):
            if CPU in files:
                rrdtool.tune(os.path.join(d, CPU),'-d', 'ds0:DERIVE', '-i', 'ds0:0')

RRDCpuType()
