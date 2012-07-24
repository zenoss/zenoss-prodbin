##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface
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

class IHeadExtraManager(IViewletManager):
    """
    A viewlet manager to allow ZenPacks, etc. to plug in extra stuff.
    """

class INewPath(Interface):
    """
    Translates old paths into new ones.
    """

class IErrorMessage(Interface):
    """
    A 404 or 500 page.
    """
