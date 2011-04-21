###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.component.zcml import utility
from .interfaces import IPreEventPlugin, IPostEventPlugin

def _eventPlugin( _context, plugin, pluginInterface, name=None):
    if name is None:
        name = '.'.join((plugin.__module__, plugin.__name__))
    utility(_context, name=name, factory=plugin, provides=pluginInterface)

def preEventPlugin(_context, plugin, name=None):
    _eventPlugin( _context, plugin, IPreEventPlugin, name )

def postEventPlugin(_context, plugin, name=None):
    _eventPlugin( _context, plugin, IPostEventPlugin, name )
