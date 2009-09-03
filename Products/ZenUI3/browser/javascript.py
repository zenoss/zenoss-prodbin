import zope.interface
from interfaces import IExtDirectAPI, IMainSnippetManager
from Products.ZenUI3.utils.javascript import JavaScriptSnippetManager


class MainSnippetManager(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IMainSnippetManager)


class ExtDirectAPI(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IExtDirectAPI)
