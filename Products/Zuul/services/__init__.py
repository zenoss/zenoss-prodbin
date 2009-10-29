from zope.interface import implements
from zope.component import queryUtility

from Products.Zuul.interfaces import IService, IDataRootFactory

class ZuulService(object):
    implements(IService)

    @property
    def _dmd(self):
        """
        A way for services to access the data layer
        """
        dmd_factory = queryUtility(IDataRootFactory)
        if dmd_factory:
            return dmd_factory()


from eventservice import EventService
