###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger('zen.ReportFacade')

from zope.interface import implements

from Products.Zuul.facades import TreeFacade
from Products.Zuul.utils import UncataloguedObjectException
from Products.Zuul.interfaces import ITreeFacade, IReportFacade
from Products.Zuul.infos.report import ReportClassNode
from Products.Zuul.routers.report import reportTypes, essentialReportOrganizers

_createMethods = [
    'manage_addDeviceReport',
    'manage_addGraphReport',
    'manage_addMultiGraphReport',
]

class ReportFacade(TreeFacade):
    implements(IReportFacade, ITreeFacade)

    @property
    def _report_factories(self):
        factories = getattr(self, '_report_factory_methods', None)
        if factories is None:
            factories = {}
            for reportType, orgUid, methodName in zip(reportTypes,
                    essentialReportOrganizers, _createMethods):
                organizer = self._dmd.restrictedTraverse(orgUid)
                factories[reportType] = getattr(organizer, methodName)
            self._report_factory_methods = factories
        return factories

    @property
    def _root(self):
        return self._dmd.Reports

    def moveNode(self, sourceUid, targetUid):
        targetNode = self._dmd.restrictedTraverse(targetUid)
        movingNode = self._dmd.restrictedTraverse(sourceUid)

        # make sure object being moved does not have duplicate id
        # with an existing object in the targetNode
        if movingNode.id in targetNode:
            msgfields = {
                'title': movingNode.titleOrId(),
                'target': targetNode.titleOrId(),
                'dupeId': movingNode.id,
            }
            failmsg = "Cannot move '%(title)s', '%(target)s' already contains an object with the id '%(dupeId)s'" % msgfields
            raise Exception(failmsg)

        # all clear, move the object from parent to the target node
        movingNode.getParentNode()._delObject(movingNode.id)
        targetNode._setObject(movingNode.id, movingNode)

    def addReport(self, reportType, contextUid, id):
        report = self._report_factories[reportType](id)
        report.getParentNode()._delObject(id)
        targetNode = self._dmd.restrictedTraverse(contextUid)
        targetNode._setObject(id, report)

