###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
###############################################################################

__doc__="""ZenDate

$Id: ZenDate.py,v 1.1 2004/04/15 00:54:14 edahl Exp $"""

from Globals import Persistent
from DateTime import DateTime
from Products.ZenUtils import Time

class ZenDate(Persistent):
    """wraper so that date sets on device don't provoke entire object store"""
    
    def __init__(self, date=None):
        self.setDate(date)
        
    def setDate(self, date=None):
        if date == None: date = DateTime()
        if type(date) == type(''):
            date = DateTime(date)
        self.date = date

    def __float__(self):
        return float(self.date)

    def getDate(self):
        return self.date
   
    def getString(self):
        """Date in format 2006/09/13 12:16:06.000
        """
        return Time.LocalDateTime(self.date.timeTime())

    def getStringSecsResolution(self):
        """Date in format 2006/09/13 12:16:06
        """
        return Time.LocalDateTimeSecsResolution(self.date.timeTime())
