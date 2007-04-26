from Products.ZenReports import Utils

class swinventory:
    def run(self, dmd, args):
        report = []
        for m in dmd.Manufacturers.objectValues():
            if m.id == 'Unknown' or m.meta_type != 'Manufacturer': continue
            for p in m.products.objectValues():
                if p.meta_type == 'SoftwareClass':
                    c = p.instances.countObjects()
                    if c == 0: continue 
                    print m.id, p.id, p.instances.countObjects()
                    report.append(
                        Utils.Record(
                            mname = m.id,
                            swname = p.id,
                            count = p.instances.countObjects()
                        )
                    )
        return report
