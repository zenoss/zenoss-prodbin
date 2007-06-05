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
