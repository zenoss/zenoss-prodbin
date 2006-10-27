#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add Mibs organizer and friends.

'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate
import os

class Mibs(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
        if hasattr(dmd, 'Mibs'):
            return

	from Testing.ZopeTestCase.ZopeLite import installProduct
	installProduct('PluginIndexes', 1)

        from Products.ZenModel.MibOrganizer import manage_addMibOrganizer
        manage_addMibOrganizer(dmd, 'Mibs')

Mibs()
