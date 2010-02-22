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
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse

class DetailNavRouter(DirectRouter):
    """
    Router to Details navigation for given uid
    """
    def getDetailNavConfigs(self, uid=None):
        """
        return a list of Detail navigation configurations. Can be used to create
        navigation links. Format is:
        {
        id: <id of the configuration>,
        'text': <display name of the config info>
        }
        """
        detailItems = []
        def convertToDetailNav(tab):
            return {
                    'id': '%s' % tab['name'].lower(),
                    'text': tab['name']
                    }
        if uid:
            ob = self.context.dmd.restrictedTraverse(uid)
            tabs = ob.zentinelTabs('')
            detailItems = [ convertToDetailNav(tab) for tab in tabs ]
        return DirectResponse(navConfigs=detailItems)

    def getDetailPanelConfigs(self, uid):
        """
        return a list of Detail navigation configurations. Can be used to create
        Ext Panels. Format is:
        {
        id: <id of the configuration>,
        'viewName': <view to display>,
        'xtype': <Ext type for the panel>,
        }
        """
        detailPanels = []
        def convertToPanelConfig(tab):
            return {
                    'xtype': 'backcompat',
                    'viewName': tab['action'],
                    'id':  tab['name'].lower()
                    }
        if uid:
            ob = self.context.dmd.restrictedTraverse(uid)
            tabs = ob.zentinelTabs('')
            detailPanels = [ convertToPanelConfig(tab) for tab in tabs ]
        return DirectResponse(panelConfigs=detailPanels)
    