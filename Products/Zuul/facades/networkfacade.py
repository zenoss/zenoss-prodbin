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
from itertools import imap

from zope.interface import implements

from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade, INetworkFacade
from Products.Zuul.interfaces import IInfo, ICatalogTool
from Products.Zuul.tree import SearchResults

log = logging.getLogger('zen.NetworkFacade')

class NetworkFacade(TreeFacade):
    implements(INetworkFacade, ITreeFacade)

    def getIpAddresses(self, limit=0, start=0, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):

        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'

        brains = cat.search("Products.ZenModel.IpAddress.IpAddress",
                            start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        objs = imap(unbrain, brains)
        infos = imap(IInfo, objs)
        # convert to info objects
        return SearchResults(infos, brains.total, brains.hash_)

    @property
    def _root(self):
        return self._dmd.Network

    @property
    def _instanceClass(self):
        return "Products.ZenModel.IpNetwork.IpNetwork"

    def _getSecondaryParent(self, obj):
        return obj

