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

from zope.interface import implements
from zope.component import queryUtility

from Products.Zuul.interfaces import IFacade, IDataRootFactory, ITreeNode
from Products.Zuul.interfaces import ITreeFacade

class ZuulFacade(object):
    implements(IFacade)

    @property
    def _dmd(self):
        """
        A way for facades to access the data layer
        """
        dmd_factory = queryUtility(IDataRootFactory)
        if dmd_factory:
            return dmd_factory()


class TreeFacade(ZuulFacade):
    implements(ITreeFacade)

    def getTree(self, root):
        context = self._traverse(root)
        if context:
            return ITreeNode(context)

    def getInfo(self, path):
        context = self._traverse(path)
        if context:
            return IInfo(context)

    def _traverse(self, path):
        return self._dmd.unrestrictedTraverse(path)



from eventfacade import EventFacade
from processfacade import ProcessFacade
