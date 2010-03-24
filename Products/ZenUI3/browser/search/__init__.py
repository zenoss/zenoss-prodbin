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

from Products.Zuul import getFacade
from Products.ZenUI3.browser.javascript import JavaScriptSrcViewlet

class IncludeSearchBox(JavaScriptSrcViewlet):
    """
    Checks for the existence of search providers.  If there are none,
    do not display the query widget.
    """
    
    path = "++resource++search/zenoss-search.js"

    def render(self):
        if not getFacade('search').noProvidersPresent():
            return super(IncludeSearchBox,self).render()
        else:
            return ''