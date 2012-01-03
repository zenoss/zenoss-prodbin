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
__doc__='''
The "rename device" and "delete device" dialogs were rewritten in ExtJs so
remove them from the ZODB.
'''
__version__ = "$Revision$"[11:-2]

import Migrate

from Products.Zuul.utils import safe_hasattr as hasattr

class RemoveDeviceZenMenus(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        rel = dmd.zenMenus.Manage.zenMenuItems
        if hasattr(rel, 'deleteDevice'):
            rel._delObject('deleteDevice')
        if hasattr(rel, 'renameDevice'):
            rel._delObject('renameDevice')
        if hasattr(rel, 'lockObject'):
            rel._delObject('lockObject')


RemoveDeviceZenMenus()
