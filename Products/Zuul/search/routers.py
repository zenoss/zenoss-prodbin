######################################################################
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
######################################################################

from Products.ZenUtils.Ext import DirectRouter
from Products import Zuul


class SearchRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('search')

    def _addAllResultsLink(self, results):
        # HERE'S WHERE WE ADD THE LINK TO THE MAIN SEARCH PAGE
        pass

    def getLiveResults(self, query):
        facade = self._getFacade()
        results = facade.getQuickSearchResults(query)
        self._addAllResultsLink( results )
        return {'results': sorted(Zuul.marshal(results),
            lambda x, y: cmp(x['category'], y['category']))}

    def noProvidersPresent(self):
        return self._getFacade().noProvidersPresent()
    
