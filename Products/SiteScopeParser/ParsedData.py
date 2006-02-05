#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""ParsedData

An object wrapping a list of SiteScopeRow objects.

$Id: ParsedData.py,v 1.2 2002/05/10 15:51:12 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import time

class ParsedData:
    def __init__(self, rows):
        if not rows: raise "NoRows"
        self._rows = rows
        self._timestamp = time.time()

    def getRows(self):
        return self._rows

    def getCols(self):
        return self._rows[0].columns()

    def fixRows(self, host, baseHref):
        for row in self._rows:
            row.fixURLs(host,baseHref)

    def getTimeStamp(self):
        return self._timestamp
