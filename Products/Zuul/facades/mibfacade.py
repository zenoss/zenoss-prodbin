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
log = logging.getLogger('zen.MibFacade')

from zope.interface import implements
from Acquisition import aq_parent

from Products.Zuul.facades import TreeFacade
from Products.Zuul.utils import UncataloguedObjectException
from Products.Zuul.interfaces import ITreeFacade, IMibFacade, IInfo
from Products.Zuul.infos.mib import MibOrganizerNode, MibNode

from Products.Jobber.jobs import ShellCommandJob
from Products.ZenUtils.Utils import binPath

from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.MibModule import MibModule


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
        except UncataloguedObjectException:
            pass

    def oidcmp(self, node1, node2):
        """
        Compare two OIDs based on the numerical value,
        rather than lexical ordering.
        """
        a = node1.oid.split('.')
        b = node2.oid.split('.')

        # Find the point where the OIDs diverge
        for i in range( min(len(a), len(b)) ):
            if a[i] == b[i]:
                continue

            # Compare the two oids at the branch, *numerically*
            return cmp( int(a[i]), int(b[i]) )

        # This case occurs when one OID is the parent of another
        return cmp( len(a), len(b) )

    def addOidMapping(self, uid, id, oid, nodetype):
        self._getObject(uid).addMibNode(id, oid, nodetype)

    def addTrap(self, uid, id, oid, nodetype):
        self._getObject(uid).addMibNotification(id, oid, nodetype)

    def deleteOidMapping(self, mibUid, mappingId):
        self._getObject(mibUid).deleteMibNodes([mappingId])

    def deleteTrap(self, mibUid, trapId):
        self._getObject(mibUid).deleteMibNotifications([trapId])

    def getMibNodes(self, uid, limit=0, start=0, sort='name', dir='DESC', relation='nodes'):
        obj = self._getObject(uid)
        if isinstance(obj, MibOrganizer):
            return []
        functor = getattr(obj, relation, None)
        if functor is None:
            log.warn("Unable to retrieve the relation '%s' from %s",
                     relation, obj.id)
            return []
        all = [IInfo(node) for node in functor()]
        reverse = dir == 'DESC'
        return len(all), sorted(all, key=lambda info: getattr(info, sort), reverse=reverse)[start:limit + start]

    def getMibNodeTree(self, id):
        return self.getMibBaseNodeTree(id, relation='nodes')

    def getMibTrapTree(self, id):
        return self.getMibBaseNodeTree(id, relation='notifications')

    def getMibBaseNodeTree(self, id, relation='nodes'):
        obj = self._getObject(id)
        if isinstance(obj, MibOrganizer):
            return []
        functor = getattr(obj, relation, None)
        if functor is None:
            log.warn("Unable to retrieve the relation '%s' from %s",
                     relation, obj.id)
            return []
        seenNodes = {}
        rootNode = None
        try:
            for node in sorted(functor(), self.oidcmp):
                prev_oid, _ = node.oid.rsplit('.', 1)
                branchNode = seenNodes.get(prev_oid)
                if branchNode:
                    subNode = MibNode(node)
                    branchNode._addSubNode(subNode)
                    seenNodes[node.oid] = subNode
                else:
                    while '.' in prev_oid:  # Look for sub-matches
                        prev_oid, _ = prev_oid.rsplit('.', 1)
                        branchNode = seenNodes.get(prev_oid)
                        if branchNode:
                            subNode = MibNode(node)
                            branchNode._addSubNode(subNode)
                            seenNodes[node.oid] = subNode
                            break
                    else: #  The first entry
                        rootNode = MibNode(node)
                        seenNodes[node.oid] = rootNode

            return rootNode
        except UncataloguedObjectException:
            pass

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
                raise Exception('Cannot move MIB %s of type %s' % args)
        return self._getObject(targetUid)
