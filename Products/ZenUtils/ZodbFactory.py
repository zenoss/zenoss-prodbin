###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
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
from Products.ZenUtils.GlobalConfig import globalConfToDict
from zope.interface import Interface
from zope.interface import implements
from zope.component import queryUtility 

class IZodbFactoryLookup(Interface):
    def get(name=None):
        """Return the a ZODB connection Factory by name or look up in global.conf."""

class ZodbFactoryLookup(object):
    implements(IZodbFactoryLookup)

    def get(self, name=None):
        """Return the ZODB connection factory by name or look up in global.conf."""
        if name is None:
            settings = globalConfToDict()
            name = settings.get('zodb-db-type', 'mysql')
        connectionFactory = queryUtility(IZodbFactory, name)
        return connectionFactory


class IZodbFactory(Interface):

    def getZopeZodbConf():
        """Return a zope.conf style stanza for the zodb connection."""

    def getZopeZodbSessionConf():
        """Return a zope.conf style stanza for the zodb_session connection."""

    def getConnection(**kwargs):
        """Return a ZODB connection."""

    def buildOptions(parser):
        """basic command line options associated with zodb connections"""

