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

import logging
log = logging.getLogger('zen.MibFacade')

from zope.interface import implements

from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade, IMibFacade
from Acquisition import aq_parent
from Products.Jobber.jobs import ShellCommandJob
from Products.ZenUtils.Utils import binPath
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.MibModule import MibModule
from Products.Zuul.infos.mib import MibOrganizerNode


class MibFacade(TreeFacade):
    implements(IMibFacade, ITreeFacade)

    def _classFactory(self, contextUid):
        return MibModule

    @property
    def _classRelationship(self):
        return 'mibs'

    @property
    def _root(self):
        return self._dmd.Mibs

    @property
    def _instanceClass(self):
        return "Products.ZenModel.MibModule.MibModule"

    def _getSecondaryParent(self, obj):
        return obj.miborganizer()

    def getOrganizerTree(self, id):
        obj = self._getObject(id)
        try:
            return MibOrganizerNode(obj)
        except UncataloguedObjectException, e:
            pass

#    def _serviceSearch(self, limit=None, start=None, sort='name', dir='ASC',
#              params=None, uid=None, criteria=()):


    def addMibPackage(self, package, organizer):
        args = [binPath('zenmib'), 'run', package,
                '--path=%s' % organizer]
        jobStatus = self._dmd.JobManager.addJob(ShellCommandJob, cmd=args)
        return True, jobStatus.id

    def moveMibs(self, sourceUids, targetUid):
        moveTarget = targetUid.replace('/zport/dmd/Mibs/', '')
        for sourceUid in sourceUids:
            sourceObj = self._getObject(sourceUid)

            if isinstance(sourceObj, MibOrganizer):
                sourceParent = aq_parent(sourceObj)
                sourceParent.moveOrganizer(moveTarget, (sourceObj.id,) )

            elif isinstance(sourceObj, MibModule):
                sourceParent = sourceObj.miborganizer()
                sourceParent.moveMibModules(moveTarget, (sourceObj.id,) )

            else:
                args = (sourceUid, sourceObj.__class__.__name__)
                raise Exception('Cannot move service %s of type %s' % args)
        return self._getObject(targetUid)
