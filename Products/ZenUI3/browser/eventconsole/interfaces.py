import zope.interface

class IEventsAPI(zope.interface.Interface):
    """
    Integration layer between model and views. 
    """
    def severities():
        """
        Returns a dictionary representing event severities.

        {int:str}
        """
    def statuses():
        """
        Returns a tuple representation of event statuses, sorted ascending by
        state.

        e.g. ('new', 'acknowledged', 'suppressed')
        """
    def query():
        """
        Returns a dictionary of events.
        """
    def detail():
        """
        Returns details about an event.
        """


class IEventConsoleInitialData(zope.interface.Interface):
    """
    Marker interface for event console JavaScript snippets defining initial
    data to be rendered by the grid.
    """
