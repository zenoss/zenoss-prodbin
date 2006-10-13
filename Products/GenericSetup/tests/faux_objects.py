""" Simple, importable content classes.

$Id: faux_objects.py 40140 2005-11-15 18:53:19Z tseaver $
"""
from OFS.Folder import Folder
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from zope.interface import implements

try:
    from OFS.interfaces import IObjectManager
    from OFS.interfaces import ISimpleItem
    from OFS.interfaces import IPropertyManager
except ImportError: # BBB
    from Products.Five.interfaces import IObjectManager
    from Products.Five.interfaces import ISimpleItem
    from Products.Five.interfaces import IPropertyManager

class TestSimpleItem(SimpleItem):
    implements(ISimpleItem)

class TestSimpleItemWithProperties(SimpleItem, PropertyManager):
    implements(ISimpleItem, IPropertyManager)

KNOWN_CSV = """\
one,two,three
four,five,six
"""

from Products.GenericSetup.interfaces import ICSVAware
class TestCSVAware(SimpleItem):
    implements(ICSVAware)
    _was_put = None
    _csv = KNOWN_CSV

    def as_csv(self):
        return self._csv

    def put_csv(self, text):
        self._was_put = text

KNOWN_INI = """\
[DEFAULT]
title = %s
description = %s
"""

from Products.GenericSetup.interfaces import IINIAware
class TestINIAware(SimpleItem):
    implements(IINIAware)
    _was_put = None
    title = 'INI title'
    description = 'INI description'

    def as_ini(self):
        return KNOWN_INI % (self.title, self.description)

    def put_ini(self, text):
        self._was_put = text

KNOWN_DAV = """\
Title: %s
Description: %s

%s
"""

from Products.GenericSetup.interfaces import IDAVAware
class TestDAVAware(SimpleItem):
    implements(IDAVAware)
    _was_put = None
    title = 'DAV title'
    description = 'DAV description'
    body = 'DAV body'

    def manage_FTPget(self):
        return KNOWN_DAV % (self.title, self.description, self.body)

    def PUT(self, REQUEST, RESPONSE):
        self._was_put = REQUEST.get('BODY', '')
        stream = REQUEST.get('BODYFILE', None)
        self._was_put_as_read = stream.read()
