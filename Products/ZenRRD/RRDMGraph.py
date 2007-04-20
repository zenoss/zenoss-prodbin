###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
