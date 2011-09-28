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

Remove Modifications menu items.

$Id:$
'''
import Migrate
from Products.Zuul.interfaces import ICatalogTool

class RemoveModificationsMenuItems(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        items = ICatalogTool(dmd).search('Products.ZenModel.ZenMenuItem.ZenMenuItem')
        for brain in items:
            menuitem = brain.getObject()
            action = menuitem.action
            if action in ('../viewHistory', 'viewHistory', 'viewNewHistory'):
                menuitem.__primary_parent__.removeRelation(menuitem)

RemoveModificationsMenuItems()
