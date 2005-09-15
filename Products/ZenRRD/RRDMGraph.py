#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDMGraph

RRDMGraph stores mgraph representations for later graphing.

$Id: RRDMGraph.py,v 1.1 2003/04/25 15:50:19 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Globals import Persistent

class RRDMGraph(Persistent):

    def __init__(self, mtargets, views):
        self._mtargets = mtargets
        self._views = views

    def getMTargets(self):
        return self._mtargets

    def getViews(self):
        return self._views
