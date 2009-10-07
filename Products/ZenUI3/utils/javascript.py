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
import zope.interface
from Products.Five.viewlet.viewlet import ViewletBase
from Products.Five.viewlet.manager import ViewletManagerBase

from interfaces import IJavaScriptSnippetManager, IJavaScriptSnippet

SCRIPT_TAG_TEMPLATE = """
<script type="text/javascript">
%s
</script>
"""

class JavaScriptSnippetManager(ViewletManagerBase):

    zope.interface.implements(IJavaScriptSnippetManager)

    def render(self):
        raw_js = '\n'.join([v.render() for v in self.viewlets])
        return SCRIPT_TAG_TEMPLATE % raw_js


class JavaScriptSnippet(ViewletBase):

    zope.interface.implements(IJavaScriptSnippet)

    def snippet(self):
        raise NotImplementedError("Subclasses must implement their own "
                                  "snippet method.")
    def render(self):
        return self.snippet()
