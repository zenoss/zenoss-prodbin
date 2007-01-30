#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add a clearid column to the status and history tables

'''

__version__ = "$Revision$"[11:-2]

import Migrate
import os

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.DirectoryView import registerDirectory

class ZenUILayer(Migrate.Step):
    "Add a new skin layer to manage UI elements"
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        zenhome = os.environ['ZENHOME']
        zenui = os.path.join(zenhome, 'Products', 
                            'ZenWidgets', 'skins', 'zenui')
        ps = getToolByName(dmd.getParentNode(), 'portal_skins')
        if 'zenui' not in ps.objectIds():
            registerDirectory(zenui, globals())
            import pdb; pdb.set_trace()
            addDirectoryViews(ps, zenui, globals())
        path = ps.getSkinPath('Basic')
        path = [x.strip() for x in path.split(',')]
        if not 'zenui' in path:
            try:
                path.insert(path.index('custom')+1, 'zenui')
            except ValueError:
                path.append('zenui')
            path = ', '.join(path)
            ps.addSkinSelection('Basic', path)

            
        
ZenUILayer()
