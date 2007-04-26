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
from Products.ZenWidgets.ZenTableManager import manage_addZenTableManager

class ZenUILayer(Migrate.Step):
    "Add a new skin layer to manage UI elements"
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        layers = ('zentablemanager','zenui')
        zport = dmd.getParentNode()
        try:zport._delObject('ZenTableManager')
        except AttributeError: pass
        for layer in layers:
            try: zport.portal_skins._delObject(layer)
            except AttributeError: pass
        manage_addZenTableManager(zport)
        
ZenUILayer()
