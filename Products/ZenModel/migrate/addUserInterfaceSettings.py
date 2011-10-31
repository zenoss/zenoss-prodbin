###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """AddUserInterfaceSettings

Adds a zodb object that is a collection of user configurable settings
that affect the behavior of the User Interface.
"""

import Migrate
from Products.ZenModel.UserInterfaceSettings import UserInterfaceSettings
from Products.Zuul.utils import safe_hasattr as hasattr

class AddUserInterfaceSettings(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if not hasattr(dmd, 'UserInterfaceSettings'):
            settings = UserInterfaceSettings('UserInterfaceSettings')

            # copy settings that were previously on the data root
            settings.enableLiveSearch = getattr(dmd, 'enableLiveSearch', True)
            settings.incrementalTreeLoad = getattr(dmd, 'incrementalTreeLoad', False)

            dmd._setObject('UserInterfaceSettings', settings)

AddUserInterfaceSettings()

