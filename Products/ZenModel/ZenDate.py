###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
###############################################################################

__doc__="""ZenDate

$Id: ZenDate.py,v 1.1 2004/04/15 00:54:14 edahl Exp $"""

from Globals import Persistent
from DateTime import DateTime

class ZenDate(Persistent):
    """wraper so that date sets on device don't provoke entire object store"""
    
    def __init__(self, date=None):
        self.setDate(date)
        
    def setDate(self, date=None):
        if date == None: date = DateTime()
        if type(date) == type(''):
            date = DateTime(date)
        self.date = date

    def getDate(self):
        return self.date
   
    def getString(self):
        return self.date.strftime('%Y/%m/%d %H:%M:%S')
