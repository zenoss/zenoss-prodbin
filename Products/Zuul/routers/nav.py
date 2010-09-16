###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Operations for Navigation

Available at:  /zport/dmd/detailnav_router
"""

from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import require
from Products.ZenUI3.security.security import permissionsForContext


class DetailNavRouter(DirectRouter):
    """
    Router to Details navigation for given uid
    """

    def _getLinkMenuItems(self, menuIds, ob):
        def filterFn(menu):
            return not menu.isdialog
        items = filter(filterFn, self._getMenuItems(menuIds, ob))
        return items

    def _getDialogMenuItems(self, menuIds, ob):
        def filterFn(menu):
            return menu.isdialog
        items = filter(filterFn, self._getMenuItems(menuIds, ob))
        return items

    def _getMenuItems(self, menuIds, ob):
        linkMenus = []
        menus = ob.getMenus(menuIds)
        if menus:
            if isinstance(menus, list):
                menus = [menus];
            else:
                menus = menus.values()
            for menuItems in menus:
                for menuItem in menuItems:
                    linkMenus.append(menuItem)
        return linkMenus

    def getDetailNavConfigs(self, uid=None, menuIds=None):
        """
        return a list of Detail navigation configurations. Can be used to create
        navigation links. Format is:
        {
        id: <id of the configuration>,
        'viewName': <view to display>,
        'xtype': <Ext type for the panel>,
        'text': <display name of the config info>
        }
        """
        detailItems = []
        def convertToDetailNav(tab):
            return {
                    'id': '%s' % tab['name'].lower(),
                    'xtype': 'backcompat',
                    'viewName': tab['action'],
                    'text': tab['name']
                    }
        def menuToNav(menu):
            return {
                    'id': '%s' % menu.id.lower(),
                    'xtype': 'backcompat',
                    'viewName': menu.action,
                    'text': menu.description
                    }

        if uid:
            ob = self.context.dmd.unrestrictedTraverse(uid)
            tabs = ob.zentinelTabs('')
            detailItems = [ convertToDetailNav(tab) for tab in tabs ]
            #get menu items that are not dialogs
            if menuIds:
                menus = self._getLinkMenuItems(menuIds, ob)
                if menus:
                    detailItems.extend([menuToNav(menu) for menu in menus])
        return DirectResponse(detailConfigs=detailItems)

    def getContextMenus(self, uid=None, menuIds=None):
        if uid:
            ob = self.context.dmd.unrestrictedTraverse(uid)
            menuItems = []
            if menuIds:
                menus = self._getDialogMenuItems(menuIds, ob)
                def menuToConfig(menu):
                    return {
                            'id': '%s' % menu.id.lower(),
                            'viewName': menu.action,
                            'text': menu.description
                            }
                if menus:
                    menuItems.extend([menuToConfig(menu) for menu in menus])
        return DirectResponse(menuItems=menuItems)

    def getSecurityPermissions(self, uid):
        """
        returns a dictionary of all the permissions a
        user has on the context
        """
        obj = self.context.dmd.unrestrictedTraverse(uid)
        permissions = permissionsForContext(obj)
        return DirectResponse.succeed(data=permissions)
