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
                            manuf = m,
                            soft = p,
                            count = p.instances.countObjects()
                        )
                    )
        return report
