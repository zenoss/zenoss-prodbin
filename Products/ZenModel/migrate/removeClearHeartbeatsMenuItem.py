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

__doc__ = """Remove the 'Clear Heartbeats' menu item used on the Device page
as it is considered confusing. See ZEN-1101.
"""
import os
import logging
import Globals
from Products.ZenUtils.Utils import unused, zenPath
from Products.ZenModel.migrate import Migrate
from Products.Zuul import getFacade

unused(Globals)

log = logging.getLogger('zen.migrate')

class removeClearHeartbeatsMenuItem(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        try:
            dmd.zenMenus.Manage.zenMenuItems._remove(dmd.zenMenus.Manage.zenMenuItems.clearHeartbeats)
        except AttributeError:
            pass # it didn't exist anyway

removeClearHeartbeatsMenuItem()
