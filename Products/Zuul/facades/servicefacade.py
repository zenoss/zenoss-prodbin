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
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade
from Products.Zuul.interfaces import IServiceFacade

log = logging.getLogger('zen.ServiceFacade')

class ServiceFacade(TreeFacade):
    implements(IServiceFacade, ITreeFacade)

    @property
    def _root(self):
        return self._dmd.Services

    @property
    def _instanceClass(self):
        return "Products.ZenModel.Service.Service"

    def _getSecondaryParent(self, obj):
        return obj.serviceclass()

