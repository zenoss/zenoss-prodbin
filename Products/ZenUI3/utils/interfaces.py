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
from zope.viewlet.interfaces import IViewletManager, IViewlet

class IJavaScriptSnippetManager(IViewletManager):
    """
    Simple way to get data from Zope to JavaScript layer. Viewlets deliver up
    bits of raw JavaScript, and the manager wraps them in a SCRIPT tag for the
    template.
    """

class IJavaScriptSnippet(IViewlet):
    """
    Holds raw JavaScript to be delivered to the template by a
    RawJavaScriptManager. Subclass and override the L{snippet} method.
    """
    def snippet():
        """
        Returns a string containing raw javascript to be written to the page.
        Should be independently syntactically sound (i.e., don't forget
        semicolons).
        """
        pass


