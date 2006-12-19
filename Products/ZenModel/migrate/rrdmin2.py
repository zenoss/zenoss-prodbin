"Change the old default of rrdmax from -1 to None"

import Migrate

def _cutoverTemplate(template):
    for s in template.datasources():
        for p in s.datapoints():
            if p.rrdmax == -1:
                p.rrdmax = None
    

class RRDMinValue2(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        for org in dmd.Devices.getSubOrganizers():
            map(_cutoverTemplate, org.getRRDTemplates())
        for dev in dmd.Devices.getSubDevices():
            map(_cutoverTemplate, dev.getRRDTemplates())
                

RRDMinValue2()
