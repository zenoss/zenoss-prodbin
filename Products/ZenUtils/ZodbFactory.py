##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
