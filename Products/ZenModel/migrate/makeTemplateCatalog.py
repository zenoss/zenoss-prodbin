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

__doc__='''

'''
import Globals
import Migrate
from Products.ZenModel.RRDTemplate import CreateRRDTemplatesCatalog, \
                                            ReindexRRDTemplates, \
                                            RRDTEMPLATE_CATALOG

class MakeTemplateCatalog(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):                
        if getattr(dmd, RRDTEMPLATE_CATALOG, None) is None:
            CreateRRDTemplatesCatalog(dmd)
            ReindexRRDTemplates(dmd)

MakeTemplateCatalog()
