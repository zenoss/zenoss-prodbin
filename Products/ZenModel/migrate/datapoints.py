
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Re-index the event history table.

'''

__version__ = "$Revision$"[11:-2]

import os
import Migrate

from Products.ZenModel.RRDDataPoint import RRDDataPoint, SEPARATOR

MOVED_PROPERTIES = 'sourcetype createCmd rrdtype isrow rpn rrdmax color linetype limit format'.split()

def copyProperty(source, dest, name):
    try:
        s = getattr(source, name)
    except AttributeError:
        return
    d = getattr(dest, name)
    if s != d:
        setattr(dest, name, s)
    try:
        delattr(s, name)
    except AttributeError:
        pass

class DataPoints(Migrate.Step):
    "Convert a data source into a data source with a data point"
    version = 23.0

    def __init__(self):
        Migrate.Step.__init__(self)
        self.renames = []

    def cutoverTemplates(self, obj):
        oldbase = os.path.join(os.getenv('ZENHOME'), 'perf')
        for t in obj.getRRDTemplates():
            for s in t.datasources():
                s.buildRelations()
                if not s.datapoints():
                    p = RRDDataPoint(s.id)
                    for prop in MOVED_PROPERTIES:
                        copyProperty(s, p, prop)
                    s.datapoints._setObject(p.id, p)
                if s.sourcetype == 'SNMP': continue
                oldname = os.path.join(oldbase + obj.rrdPath(), s.id)
                newname = '%s%c%s' % (oldname, SEPARATOR, s.id)
                oldname += ".rrd"
                newname += ".rrd"
                if os.path.exists(oldname):
                    self.renames.append( (oldname, newname) )
                    os.rename(oldname, newname)

    def cutover(self, dmd):
        for d in dmd.Devices.getSubDevices():
            self.cutoverTemplates(d)
            for o in d.getDeviceComponents():
                self.cutoverTemplates(o)

    def revert(self):
        for oldname, newname in self.renames:
            os.renames(newname, oldname)

DataPoints()
