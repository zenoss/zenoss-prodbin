###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.CMFCore.utils import getToolByName

class Linkable:
    """ A mixin allowing an object to be the 
        endpoint of a Link object.
    """

    def _getLinkCatalog(self):
        try:
            return getToolByName(self.dmd.ZenLinkManager, self.link_catalog)
        except AttributeError:
            return None

    def index_links(self):
        cat = self._getLinkCatalog()
        if cat is not None:
            cat.catalog_object(self)


class Layer2Linkable(Linkable):

    link_catalog = "layer2_catalog"

    def deviceId(self): raise NotImplementedError
    def interfaceId(self): raise NotImplementedError
    def macaddress(self): raise NotImplementedError
    def lanId(self): raise NotImplementedError


class Layer3Linkable(Linkable):

    link_catalog = "layer3_catalog"

    def deviceId(self): raise NotImplementedError
    def ipAddressId(self): raise NotImplementedError
    def networkId(self): raise NotImplementedError
    def interfaceId(self): raise NotImplementedError


