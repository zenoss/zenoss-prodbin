from zope.interface import Interface

class IService(Interface):
    """
    An API service
    """

class IDataRootFactory(Interface):
    """
    Returns a DataRoot object from the current connection.
    """

from events import *
