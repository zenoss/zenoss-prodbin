###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import transaction
from types import ClassType
from operator import attrgetter
from itertools import islice
from Acquisition import aq_base, aq_chain
from zope.interface import Interface
from AccessControl import getSecurityManager
from zope.i18nmessageid import MessageFactory
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager

# Translations
ZuulMessageFactory = MessageFactory('zenoss')

def resolve_context(context, default=None, dmd=None):
    """
    Make sure that a given context is an actual object, and not a path to
    the object, by trying to traverse from the dmd if it's a string.
    """
    try:
        dmd = dmd or get_dmd()
    except AttributeError:
        # was not able to get the dmd
        dmd = None
    if dmd:
        if isinstance(context, basestring):
            # Should be a path to the object we want
            if context.startswith('/') and not context.startswith('/zport/dmd'):
                context = context[1:]
            try:
                context = dmd.unrestrictedTraverse(context)
            except (KeyError, AttributeError):
                context = None
    if context is None:
        context = default
    return context

_sevs = ['clear', 'debug', 'info', 'warning', 'error', 'critical']

def severityId(severity):
    """Takes an event severity string and returns the "id" of it. As expected
    by the event and the threshold classes
    """
    if isinstance(severity, basestring):
        return  _sevs.index(severity.lower())

def severityString(severityId):
    """Takes an event severity id (the numeric value) and converts it to
    the lower case string representation
    """
    if severityId in range(0,6):
        return _sevs[severityId]


def get_dmd():
    """
    Retrieve the DMD object.
    """
    connections = transaction.get()._synchronizers.data.values()[:]
    connections.reverse()
    # Make sure we don't get the temporary connection
    for cxn in connections:
        if cxn._db.database_name != 'temporary':
            app = cxn.root()['Application']
            return app.zport.dmd


_MARKER = object()
def safe_hasattr(object, name):
    return getattr(object, name, _MARKER) is not _MARKER


def unbrain(item):
    if isinstance(item, AbstractCatalogBrain):
        return item.getObject()
    return item


class LazySortableList(object):

    def __init__(self, iterable, cmp=None, key=None, orderby=None, 
                 reverse=False):
        self.iterator = iter(iterable)
        if cmp is not None or key is not None or orderby is not None:
            # Might as well exhaust it now
            if orderby is not None:
                key = attrgetter(orderby)
            self.seen = sorted(self.iterator, cmp=cmp, key=key, 
                               reverse=reverse)
        else:
            self.seen = []

    def __getitem__(self, index):
        self.exhaust(index)
        return self.seen[index]

    def __getslice__(self, start, stop):
        self.exhaust(stop-1)
        return self.seen[start:stop]

    def __len__(self):
        return len(self.seen)

    def __repr__(self):
        return repr(self.seen)

    def exhaust(self, i):
        if i<0:
            raise ValueError("Negative indices not supported")
        delta = i-len(self)
        if delta > 0:
            self.seen.extend(islice(self.iterator, delta+1))


class BrainWhilePossible(object):
    def __init__(self, ob):
        self._ob = ob

    @property
    def _is_brain(self):
        return isinstance(self._ob, AbstractCatalogBrain)

    def __getattr__(self, attr):
        if self._is_brain:
            try:
                return getattr(aq_base(self._ob), attr)
            except AttributeError:
                # Not metadata; time to go get the ob
                self._ob = unbrain(self._ob)
        return getattr(self._ob, attr)


def dottedname(ob):
    # If already a dotted name, just return it
    if isinstance(ob, basestring):
        return ob
    # If an interface, use cached value
    elif isinstance(ob, Interface):
        return ob.__identifier__
    # Don't know, so create name ourselves from the class
    if not isinstance(ob, (type, ClassType)):
        ob = ob.__class__
    return '%s.%s' % (ob.__module__, ob.__name__)


def getZProperties(context):
    """
    Given a context, this function will return all of the ZProperties that
    are defined for this context (ignoring acquisition)
    @returns Dictionary of the form { 'zPropertyName' : 'zPropertyValue',}
    """
    properties = {}
    # make sure we actually have properties
    if not isinstance(context, ZenPropertyManager):
        return properties

    # get all of the property ids from Devices
    propertyIds = context.dmd.Devices.zenPropertyIds()
    for propertyId in propertyIds:
        # has property does not take acquisition into account by default
        if context.hasProperty(propertyId):
            properties[propertyId] = context.getProperty(propertyId)

    return properties

def getAcquiredZPropertyInfo(obj, zProp, translate=lambda x: x):
    for ancestor in aq_chain(obj)[1:]:
        if isinstance(ancestor, ZenPropertyManager) and ancestor.hasProperty(zProp):
            info = {'acquiredValue': translate(getattr(ancestor, zProp)),
                    'ancestor': ancestor.titleOrId()
                    }
            break
    else:
        info = {'acquiredValue': None, 'ancestor': None}
    return info

def getZPropertyInfo(obj, zProp, defaultLocalValue='', translate=lambda x: x, translateLocal=False):
    zPropInfo = {}
    zPropInfo['isAcquired'] = not obj.hasProperty(zProp)
    if zPropInfo['isAcquired']:
        zPropInfo['localValue'] = defaultLocalValue
    else:
        zPropInfo['localValue'] = getattr(obj, zProp)
        if translateLocal:
            zPropInfo['localValue'] = translate(zPropInfo['localValue'])
    zPropInfo.update(getAcquiredZPropertyInfo(obj, zProp, translate))
    return zPropInfo

def setZPropertyInfo(obj, zProp, isAcquired, localValue, **kwargs):
    if isAcquired:
        if obj.hasProperty(zProp):
            obj.deleteZenProperty(zProp)
    else:
        if obj.hasProperty(zProp):
            obj._updateProperty(zProp, localValue)
        else:
            obj._setProperty(zProp, localValue)


def allowedRolesAndGroups(context):
    """
    Returns a list of all the groups and
    roles that the logged in user has access too
    @param context: context for which we are retrieving
    allowed roles and groups
    @return [string]: All roles user has as well as groups
    """
    user = getSecurityManager().getUser()
    roles = list(user.getRolesInContext(context))
    # anonymous and anything we own
    roles.append('Anonymous')
    roles.append('user:%s' % user.getId())
    # groups
    groups = user.getGroups()
    for group in groups:
        roles.append('user:%s' % group)
        
    return roles
