###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Operations for ZenPacks.

Available at:  /zport/dmd/zenpack_router
"""

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require
from Products.ZenMessaging.audit import audit

log = logging.getLogger('zen.ZenPackRouter')
class ZenPackRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on ZenPacks
    """

    def _getFacade(self):
        return Zuul.getFacade('zenpack', self.context)

    def getEligiblePacks(self, **data):
        """
        Get a list of eligible ZenPacks to add to.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - packs: ([dictionary]) List of objects representing ZenPacks
             - totalCount: (integer) Total number of eligible ZenPacks
        """
        devZenPacks = self._getFacade().getDevelopmentZenPacks()
        packs = [{'name': zp.getId()} for zp in devZenPacks]
        packs = sorted(packs, key=lambda pack: pack['name'])
        return DirectResponse(packs=packs, totalCount=len(packs))

    @require('Manage DMD')
    def addToZenPack(self, topack, zenpack):
        """
        Add an object to a ZenPack.

        @type  topack: string
        @param topack: Unique ID of the object to add to ZenPack
        @type  zenpack: string
        @param zenpack: Unique ID of the ZenPack to add object to
        @rtype:   DirectResponse
        @return:  Success message
        """
        self._getFacade().addToZenPack(topack, zenpack)
        audit('UI.ZenPack.AddObject', zenpack, object=topack)
        return DirectResponse.succeed()
