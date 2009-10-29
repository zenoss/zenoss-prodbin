from zope.interface import implements
from zope.component import queryUtility

from Products.ZenModel.interfaces import IDataRoot

from Products.Zuul.interfaces import IService, IServiceable


def resolve_context(context):
    """
    Make sure that a given context is an actual object, and not a path to
    the object, by trying to traverse from the dmd if it's a string.
    """
    dmd = queryUtility(IDataRoot)
    if dmd:
        if isinstance(context, basestring):
            # Should be a path to the object we want
            try:
                context = dmd.unrestrictedTraverse(context)
            except (KeyError, AttributeError):
                context = None
    return context


class ZuulService(object):
    implements(IService)

    @property
    def _dmd(self):
        """
        A way for services to access the data layer
        """
        return queryUtility(IDataRoot)

from eventservice import EventService
