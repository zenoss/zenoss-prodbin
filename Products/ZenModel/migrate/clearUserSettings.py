###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.Zuul.facades import ObjectNotFoundException

__doc__ = """
The user preference settings for trees and grids conflict between ExtJS3 and 4, this migrate
script removes them all.
"""

import Migrate
import logging
from Products.Zuul.interfaces import ICatalogTool
log = logging.getLogger('zen.migrate')




class ClearUserSettings(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr(dmd, '_clearedUserSettingsExtJs4'):
            for brain in ICatalogTool(dmd).search('Products.ZenModel.UserSettings.UserSettings'):
                user = brain.getObject()
                if hasattr(user, '_browser_state'):
                    del brain.getObject()._browser_state
            dmd._clearedUserSettingsExtJs4 = True

ClearUserSettings()
