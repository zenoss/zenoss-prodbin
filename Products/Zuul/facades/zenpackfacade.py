##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
