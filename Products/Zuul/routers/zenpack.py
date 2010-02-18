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
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require

log = logging.getLogger('zen.ZenPackRouter')
class ZenPackRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('zenpack')

    def getEligiblePacks(self, **data):
        devZenPacks = self._getFacade().getDevelopmentZenPacks()
        packs = [{'name': zp.getId()} for zp in devZenPacks]
        return DirectResponse(packs=packs, totalCount=len(packs))

    @require('Manage DMD')
    def addToZenPack(self, topack, zenpack):
        self._getFacade().addToZenPack(topack, zenpack)
        return DirectResponse.succeed()
