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
from itertools import izip, count
from Acquisition import aq_parent
from zope.interface import implements
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.interfaces import ITreeFacade

log = logging.getLogger('zen.ProcessFacade')

class ProcessFacade(TreeFacade):
    implements(IProcessFacade, ITreeFacade)

    @property
    def _root(self):
        return self._dmd.Processes

    @property
    def _classFactory(self):
        return OSProcessClass

    @property
    def _classRelationship(self):
        return 'osProcessClasses'

    @property
    def _instanceClass(self):
        return "Products.ZenModel.OSProcess.OSProcess"

    def _getSecondaryParent(self, obj):
        return obj.osProcessClass()

    def moveProcess(self, uid, targetUid):
        obj = self._getObject(uid)
        target = self._getObject(targetUid)
        if isinstance(obj, OSProcessClass):
            source = obj.osProcessOrganizer()
            source.moveOSProcessClasses(targetUid, obj.id)
            newObj = getattr(target.osProcessClasses, obj.id)
        elif isinstance(obj, OSProcessOrganizer):
            source = aq_parent(obj)
            source.moveOrganizer(targetUid, (obj.id,))
            newObj = getattr(target, obj.id)
        else:
            raise Exception('Illegal type %s' % obj.__class__.__name__)
        return newObj.getPrimaryPath()

    def getSequence(self):
        processClasses = self._dmd.Processes.getSubOSProcessClassesSorted()
        for processClass in processClasses:
            yield {
                'uid': '/'.join(processClass.getPrimaryPath()),
                'folder': processClass.getPrimaryParent().getOrganizerName(),
                'name': processClass.name,
                'regex': processClass.regex,
                'monitor': processClass.zMonitor,
                'count': processClass.count()
            }

    def setSequence(self, uids):
        for sequence, uid in izip(count(), uids):
            ob = self._getObject(uid)
            ob.sequence = sequence

    def _getObject(self, uid):
        try:
            obj = self._dmd.unrestrictedTraverse(uid)
        except Exception, e:
            args = (uid, e.__class__.__name__, e)
            raise Exception('Cannot find "%s". %s: %s' % args)
        return obj
