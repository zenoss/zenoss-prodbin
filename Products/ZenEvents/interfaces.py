
from zope.interface import Interface

class IDbAccess(Interface):
    """
    Database access class that normalizes differences in connecting
    to databases and handles conversion of their values.
    """

    def connect(self, username, password, database, port):
        """Load our database driver and connect to the database.""" 


    def cleanstring(self,value):
        """Perform any cleanup nessesary on returned database strings."""
       

    def convert(self, field, value):
        """Perform convertion of a database value if nessesary."""
  

    def dateString(self, value):
        """Convert dates to their string format."""


    def dateDB(self, value):
        """Convert a date to its database format."""
    

    def escape(self, value):
        """Prepare string values for db by escaping special characters."""


    def checkConn(self):
        """Check to see if the connection information in product works"""



class IEventList(Interface):
    """
    Query event system for lists of events and event details.
    """
    
    def getEventList(self, resultFields=[], where="", orderby="", severity=0,
                    startdate=None, enddate=None, offset=0, rows=0):
        """
        Return a list of events that have resultFields based on where 
        and severity and ordered by orderby. Offset and rows can be used
        to limit the size of the result set.  startdate and enddate can
        limit the time range of the event list.
        """
    
    def getEventDetail(self, where=""):
        """
        Return an event with its full details populated.
        """


class IEventStatus(Interface):
    """
    Query real-time event system for status information.
    """
    
    def getEventRainbow(self, where=""):
        """
        Return a list of tuples with number of events for each severity
        and the color of the severity that the number represents.
        ((5,"#FF0000"), (14,"#FFFF00")...)
        """ 
    
    def getOrganizerStatus(self, orgType, orgName, severity=None, where=""):
        """
        Return a count of events that match where for orgName and children.
        """


    def getDeviceStatus(self, device, severity=None, where=""):
        """
        Return a count of events that match where for a particular device.
        """


    def getComponentStatus(self, device, severity=None, where=""):
        """
        Return a count of events that match where for a particular component.
        """


class ISendEvents(Interface):
    """
    Send events to the event system backend.
    """
   
    def sendEvents(self, events):
        """
        Send a list of events to the event system backend.
        """


    def sendEvent(self, event, keepopen=0):
        """
        Send a single event to the event system backend.
        """


