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
from Products.Zuul.facades import ZuulFacade
from itertools import ifilter
from itertools import imap
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.utils import unbrain
from Products.ZenModel.ZenPack import ZenPack

log = logging.getLogger('zen.ZenPackFacade')

class ZenPackFacade(ZuulFacade):

    def getDevelopmentZenPacks(self, uid='/zport/dmd/ZenPackManager'): 
        catalog = ICatalogTool(self._dmd.unrestrictedTraverse(uid))
        brains = catalog.search(types=ZenPack)
        zenpacks = imap(unbrain, brains)
        return ifilter(lambda zp: zp.isDevelopment(), zenpacks)

    def addToZenPack(self, topack, zenpack):
        self._dmd.ZenPackManager.addToZenPack(ids=[topack], pack=zenpack)
