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
from Products.ZenUI3.utils.interfaces import IJavaScriptSnippetManager
from zope.viewlet.interfaces import IViewlet, IViewletManager

class IMainSnippetManager(IJavaScriptSnippetManager):
    """
    A viewlet manager to handle general javascript snippets.
    """

class IJavaScriptSrcManager(IViewletManager):
    """
    a viewlet manager to handle java script src viewlets
    """

class IJavaScriptSrcViewlet(IViewlet):
    """
    A viewlet that will generate java a script src file includes
    """

    
class IJavaScriptBundleViewlet(IViewlet):
    """
    A viewlet that will generate a list of java script src file includes
    """