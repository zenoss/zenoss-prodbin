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
from zope.interface import implements
from Products.ZenModel.OSProcessClass import OSProcessClass
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
