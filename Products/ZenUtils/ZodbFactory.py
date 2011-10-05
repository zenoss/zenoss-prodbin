###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ZodbConnection
"""

from zope.interface import Interface

class IZodbFactory(Interface):

    def getConnection(**kwargs):
        """Return a ZODB connection."""

    def buildOptions(self, parser):
        """basic command line options associated with zodb connections"""

