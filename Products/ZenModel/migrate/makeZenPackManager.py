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
from Products.ZenModel.ZenPackManager import manage_addZenPackManager
from Products.ZenModel.ZenPackPersistence import ZENPACK_PERSISTENCE_CATALOG, \
                                            CreateZenPackPersistenceCatalog

class MakeZenPackManager(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if not getattr(dmd, 'ZenPackManager', None):
            manage_addZenPackManager(dmd, 'ZenPackManager')
            for zp in dmd.packs():
                zp.buildRelations()
                zp.moveMeBetweenRels(dmd.packs, dmd.ZenPackManager.packs)
                
        if getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None) is None:
            CreateZenPackPersistenceCatalog(dmd)
        
        for pack in dmd.ZenPackManager.packs():
            if not pack.aqBaseHasAttr('dependencies'):
                pack.dependencies = {}

MakeZenPackManager()
