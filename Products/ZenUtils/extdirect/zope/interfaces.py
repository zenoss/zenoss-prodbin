from zope.viewlet.interfaces import IViewletManager

class IExtDirectJavaScriptManager(IViewletManager):
    """
    A viewlet manager to register API providers.
    """

class IExtDirectJavaScriptAndSourceManager(IExtDirectJavaScriptManager):
    """
    A viewlet manager to publish Ext javascript resources and register API
    providers.
    """
