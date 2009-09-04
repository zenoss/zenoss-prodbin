import zope.interface

class IEventManagerProxy(zope.interface.Interface):
    """
    Holds several methods useful for interacting with a Zenoss event manager.
    """
    def _is_history():
        """
        Should we be dealing with a history manager?
        """
    def _evmgr():
        """
        Get an event manager
        """
    def _extract_data_from_zevent():
        """
        Turn an event into a dictionary containing necessary fields.
        """


class IEventConsoleInitialData(zope.interface.Interface):
    """
    Marker interface for event console JavaScript snippets defining initial
    data to be rendered by the grid.
    """
