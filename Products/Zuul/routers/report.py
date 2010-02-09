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
from Products.ZenUtils.Ext import DirectRouter
from Products.Zuul.decorators import require

log = logging.getLogger('zen.ReportRouter')
class ReportRouter(DirectRouter):

    def getTree(self, id='/zport/dmd/Reports'):
        my_data = []
        self._getReportOrganizersTree(self.context.dmd.restrictedTraverse(id),
                my_data)
        return my_data

    def _getReportOrganizersTree(self, rorg, my_data):
        for rorg in rorg.children():
            rorg_node = self._createTreeNode(rorg, False)
            my_data.append(rorg_node)
            self._getReportOrganizersTree(rorg, rorg_node['children'])

            for report in rorg.reports():
                report_node = self._createTreeNode(report, True)
                rorg_node['children'].append(report_node)

    @require('Manage DMD')
    def addNode(self, type, contextUid, id):
        if type.lower() != 'organizer':
            return {'success': False, 'msg': 'Not creating report'}

        result = {}
        try:
            uid = contextUid + '/' + id
            maoUid = uid.replace('/zport/dmd', '')
            self.context.dmd.Reports.manage_addOrganizer(maoUid)
            represented = self.context.dmd.restrictedTraverse(uid)
            node = self._createTreeNode(represented, False)
            result['nodeConfig'] = node
            result['success'] = True
            result['tree'] = self.getTree()
        except Exception, e:
            result['msg'] = str(e)
            result['success'] = False
        return result

    @require('Manage DMD')
    def addOrganizer(self, contextUid, id):
        uid = contextUid + '/' + id
        self.context.dmd.Reports.manage_addOrganizer(uid.replace('/zport/dmd', 
                ''))
        return uid

    @require('Manage DMD')
    def deleteNode(self, uid):
        represented = self.context.dmd.restrictedTraverse(uid)
        if not isinstance(represented, represented.getReportClass()):
            return {'success': False, 'msg': 'Not deleting report'}

        self.context.dmd.Reports.manage_deleteOrganizer(uid)
        return {'success': True, 'tree': self.getTree()}

    @require('Manage DMD')
    def moveReports(self, uids, target):
        """Move a report from its current organizer to moveTarget.
        """
        targetNode = self.context.dmd.restrictedTraverse(target)
        for uid in uids:
            report = self.context.dmd.restrictedTraverse(uid)
            reportTitle = report.titleOrId()
            report.getParentNode()._delObject(reportTitle)
            targetNode._setObject(reportTitle, report)
        return {'success': True, 'tree': self.getTree()}

    def _createTreeNode(self, represented, leaf):
        path = represented.getDmdKey()
        if path.startswith('/') :
            path = path[1:]

        text = represented.titleOrId()
        if not leaf:
            description = ('reports', 'report')[represented.countReports() == 1]
            text = {'count': represented.countReports(),
                    'text': represented.titleOrId(),
                    'description': description}

        return {'uid': represented.getPrimaryId(),
                'children': [],
                'path': path,
                'id': represented.titleOrId(),
                'uiProvider': 'report', 
                'leaf': leaf,
                'text': text }

    def getEligiblePacks(self, **data):
        packs = [{'name': zp.getId()} for zp in
                 self.context.dmd.ZenPackManager.packs() if zp.isDevelopment()]
        return {'packs': packs, 'totalCount': len(packs)}

