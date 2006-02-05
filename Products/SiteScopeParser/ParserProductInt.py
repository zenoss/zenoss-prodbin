#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""ParserProduct

A class implementing the SiteScopeParse module as a zope product.

$Id: ParserProductInt.py,v 1.3 2002/05/03 12:12:17 alex Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from Interface import Base

class ParserProductInt(Base):
    "A parser for SiteScope's views"

    def __init__(self, id, title, url, first, timeout):
        "ParseProduct constructor"

    def getRowByName(self, name):
        "Gets a single row from the table by name, returns it as a SiteScopeRow"

    def getRowList(self):
        "Returns the entire table as a list"
    
    def displayTable(self):
        "Outputs HTML for the table representation...mostly for debugging"
