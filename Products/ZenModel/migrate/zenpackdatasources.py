#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''All existing datasources should be switched to instances
of BasicDataSource instead of RRDDataSource
'''

import Migrate

class ZenPackDataSources(Migrate.Step):

    version = Migrate.Version(1, 2, 0)


    def cutover(self, dmd):
        from Products.ZenModel.BasicDataSource import BasicDataSource
        from Products.ZenModel.RRDDataSource import RRDDataSource
        try:
            from Products.ZenWeb.datasources.PageCheckDataSource \
                import PageCheckDataSource
        except ImportError:
            PageCheckDataSource = None
        numDS = 0
        for t in dmd.Devices.getAllRRDTemplates():
            for s in t.datasources():
                if s.__class__ == RRDDataSource:
                    numDS += 1
                    if PageCheckDataSource and s.sourcetype == 'PAGECHECK':
                        s.__class__ = PageCheckDataSource
                    else:
                        s.__class__ = BasicDataSource
                elif issubclass(s.__class__, RRDDataSource):
                    pass
                else:
                    raise 'ZenPackDataSources can\'t handle datasource' + \
                            ' type %s' %(s.__class__)
        print 'Converted %s DataSources' % numDS

ZenPackDataSources()
