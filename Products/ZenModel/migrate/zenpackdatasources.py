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
