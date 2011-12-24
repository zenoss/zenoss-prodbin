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
import re
import os.path
from Products.ZenUtils.Utils import zenPath
from zope.interface import Interface
from zope.interface import implements
from zope.component import queryUtility 

class IZodbFactoryLookup(Interface):
    def get(name=None):
        """Return the a ZODB connection Factory by name or look up in global.conf."""


_KEYVALUE = re.compile("^[\s ]*(?P<key>[a-z_]+[a-z0-9_]*)[\s]+(?P<value>[^\s#]+)", re.IGNORECASE).search

def globalConfToDict():
    settings = {}
    globalConfFile = zenPath('etc','global.conf')
    if os.path.exists(globalConfFile):
        with open(globalConfFile, 'r') as f:
            for line in f.xreadlines():
                match = _KEYVALUE(line)
                if match:
                    value = match.group('value')
                    if value.isdigit():
                        value = int(value)
                    settings[match.group('key')] = value
    return settings

class ZodbFactoryLookup(object):
    implements(IZodbFactoryLookup)

    def get(self, name=None):
        """Return the ZODB connection factory by name or look up in global.conf."""
        if name is None:
            settings = globalConfToDict()
            name = settings.get('zodb_db_type', 'mysql')
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

