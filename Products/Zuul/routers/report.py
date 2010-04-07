###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.utils import ZuulMessageFactory as _t

log = logging.getLogger('zen.ReportRouter')
class ReportRouter(DirectRouter):

    _newReportTypes = [
        'customDeviceReport',
        'graphReport',
        'multiGraphReport',
    ]

    _reportMenuItems = [
        _t('Custom Device Report'),
        _t('Graph Report'),
        _t('Multi-Graph Report'),
    ]

    _createOrganizers = {
        _newReportTypes[0]: 'Custom Device Reports',
        _newReportTypes[1]: 'Graph Reports',
        _newReportTypes[2]: 'Multi-Graph Reports',
    }

    _createMethods = {
        _newReportTypes[0]: 'manage_addDeviceReport',
        _newReportTypes[1]: 'manage_addGraphReport',
        _newReportTypes[2]: 'manage_addMultiGraphReport',
    }

    def getReportTypes(self):
        return DirectResponse.succeed(reportTypes=ReportRouter._newReportTypes,
                menuText=ReportRouter._reportMenuItems)

    def getTree(self, id='/zport/dmd/Reports'):
        my_data = []
        self._getReportOrganizersTree(self.context.dmd.restrictedTraverse(id),
                my_data)
        return my_data

    def _getReportOrganizersTree(self, rorg, my_data):
        for rorg in rorg.children():
            rorg_node = self._createTreeNode(rorg)
            my_data.append(rorg_node)
            self._getReportOrganizersTree(rorg, rorg_node['children'])

            for report in rorg.reports():
                report_node = self._createTreeNode(report)
                rorg_node['children'].append(report_node)

    @require('Manage DMD')
    def addNode(self, nodeType, contextUid, id):
        if nodeType not in ['organizer'] + ReportRouter._newReportTypes :
            return DirectResponse.fail('Not creating "%s"' % nodeType)

        try:
            if nodeType == 'organizer':
                uid = contextUid + '/' + id
                maoUid = uid.replace('/zport/dmd', '')
                self.context.dmd.Reports.manage_addOrganizer(maoUid)
                represented = self.context.dmd.restrictedTraverse(uid)
            else:
                creatingOrganizer = self.context.dmd.restrictedTraverse(
                        "/zport/dmd/Reports/" + 
                        ReportRouter._createOrganizers[nodeType])
                createMethod = eval('creatingOrganizer.' + 
                        ReportRouter._createMethods[nodeType])
                represented = createMethod(id)
                represented.getParentNode()._delObject(id)
                targetNode = self.context.dmd.restrictedTraverse(contextUid)
                targetNode._setObject(id, represented)

            node = self._createTreeNode(represented)
            return DirectResponse.succeed(tree=self.getTree(), newNode=node)
        except Exception, e:
            return DirectResponse.fail(str(e))

    @require('Manage DMD')
    def deleteNode(self, uid):
        represented = self.context.dmd.restrictedTraverse(uid)
        represented.getParentNode().zmanage_delObjects([represented.titleOrId()])
        return DirectResponse.succeed(tree=self.getTree())

    @require('Manage DMD')
    def moveNode(self, uids, target):
        """Move a node from its current organizer to another.
        """
        targetNode = self.context.dmd.restrictedTraverse(target)
        for uid in uids:
            represented = self.context.dmd.restrictedTraverse(uid)
            representedTitle = represented.titleOrId()
            represented.getParentNode()._delObject(representedTitle)
            targetNode._setObject(representedTitle, represented)
            representedNode = self._createTreeNode(represented)
        return DirectResponse.succeed(tree=self.getTree(), 
                newNode=representedNode)

    def _createTreeNode(self, represented):
        path = represented.getDmdKey()
        if path.startswith('/') :
            path = path[1:]

        text = represented.titleOrId()
        leaf = not isinstance(represented, represented.getReportClass())
        if not leaf:
            description = ('reports', 'report')[represented.countReports() == 1]
            text = {'count': represented.countReports(),
                    'text': represented.titleOrId(),
                    'description': description}

        return {'uid': represented.getPrimaryId(),
                'children': [],
                'path': path,
                'id': represented.getPrimaryId().replace('/', '.'),
                'uiProvider': 'report', 
                'leaf': leaf,
                'expandable': not leaf,
                'meta_type': represented.meta_type,
                'text': text }
