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
                                            RRDTEMPLATE_CATALOG

class MakeTemplateCatalog(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    # This creates the catalog if it doesn't exist.  Indexing of the templates
    # happens in the twotwoindexing.py step.

    def cutover(self, dmd):                
        if getattr(dmd, RRDTEMPLATE_CATALOG, None) is None:
            CreateRRDTemplatesCatalog(dmd)

makeTemplateCatalog = MakeTemplateCatalog()
