'''
from zope.component.factory import Factory
from zope.component.interfaces import IFactory

from .datamaps import ZingDatamapHandler
from .zing_connector import ZingConnectorClient

def _register_factories():
    """
    To create a ZingConnectorClient or a ZingDatamapHandler:
        >>> from zope.component import createObject
        >>> client = createObject('ZingConnectorClient')
    """
    # Register Factories
    factory = Factory(ZingConnectorClient, "Zing Conector Client factory")
    getGlobalSiteManager().registerUtility(factory, IFactory, 'ZingConnectorClient')


#_register_factories()
'''