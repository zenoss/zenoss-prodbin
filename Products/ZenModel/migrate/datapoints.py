
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

MOVED_PROPERTIES = 'createCmd rrdtype isrow rpn rrdmax color linetype limit format'.split()
NAGIOS_PROPERTIES = 'enabled usessh component eventClass eventKey severity commandTemplate cycletime'.split()

def copyProperty(source, dest, name):
    try:
        s = getattr(source, name)
    except AttributeError:
        return
    try:
        d = getattr(dest, name)
    except AttributeError:
        import pdb
        pdb.set_trace()
        pass

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

    def cutoverDataSource(self, s):
        s.buildRelations()
        if not s.datapoints():
            p = RRDDataPoint(s.id)
            for prop in MOVED_PROPERTIES:
                copyProperty(s, p, prop)
            s.datapoints._setObject(p.id, p)

    def cutoverTemplates(self, obj):
        oldbase = os.path.join(os.getenv('ZENHOME'), 'perf')
        for t in obj.getRRDTemplates():
            for s in t.datasources():
                self.cutoverDataSource(s)
                oldname = os.path.join(oldbase + obj.rrdPath(), s.id)
                newname = '%s%c%s' % (oldname, SEPARATOR, s.id)
                oldname += ".rrd"
                newname += ".rrd"
                if os.path.exists(oldname):
                    self.renames.append( (oldname, newname) )
                    os.rename(oldname, newname)

    def cutoverNagios(self, obj):
        sourceTemplate = obj.getNagiosTemplate()
        destTemplate = obj.getRRDTemplate(obj.getRRDTemplateName())
        for n in sourceTemplate.nagiosCmds():
            try:
                ds = destTemplate.datasources._getOb(n.id)
            except AttributeError:
                destTemplate.manage_addRRDDataSource(n.id)
                ds = destTemplate.datasources._getOb(n.id)
                ds.sourcetype = 'NAGIOS'
            if ds.sourcetype == 'NAGIOS':
                for attr in NAGIOS_PROPERTIES:
                    setattr(ds, attr, getattr(n, attr))

    def cutover(self, dmd):
        for org in dmd.Devices.getSubOrganizers():
            for t in org.getRRDTemplates():
                for s in t.datasources():
                    self.cutoverDataSource(s)
        for d in dmd.Devices.getSubDevices():
            self.cutoverTemplates(d)
            self.cutoverNagios(d)
            for o in d.getDeviceComponents():
                self.cutoverTemplates(o)
                self.cutoverNagios(o)
            

    def revert(self):
        for oldname, newname in self.renames:
            os.renames(newname, oldname)

DataPoints()
