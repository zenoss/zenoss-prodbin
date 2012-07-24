##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenReports import Utils

class swinventory:
    def run(self, dmd, args):
        report = []
        for m in dmd.Manufacturers.objectValues():
            if m.id == 'Unknown' or m.meta_type != 'Manufacturer': continue
            for p in m.products.objectValues():
                if p.meta_type == 'SoftwareClass':
                    c = 0
                    for i in p.instances():
                        try:
                            if dmd.checkRemotePerm('View', i.device()):
                                c += 1
                        except:
                            continue
                    if c == 0: continue 
                    print m.id, p.id, c
                    report.append(
                        Utils.Record(
                            manuf = m,
                            manufId = m.id,
                            soft = p,
                            softId = p.id,
                            count = c
                        )
                    )
        return report
