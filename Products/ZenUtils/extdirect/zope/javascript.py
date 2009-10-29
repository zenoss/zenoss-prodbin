import zope.interface
from zope.viewlet.manager import WeightOrderedViewletManager
from zope.viewlet.viewlet import JavaScriptViewlet
from interfaces import IExtDirectJavaScriptManager
from interfaces import IExtDirectJavaScriptAndSourceManager

class ExtDirectJavaScriptManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptManager)

class ExtDirectJavaScriptAndSourceManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptAndSourceManager)

DirectSourceViewlet = JavaScriptViewlet('direct.js')
