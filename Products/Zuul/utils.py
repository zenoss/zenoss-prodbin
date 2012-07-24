##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import transaction
from copy import deepcopy
from types import ClassType
from operator import attrgetter
from itertools import islice
from Acquisition import aq_base, aq_chain
from zope.interface import Interface
from BTrees.OOBTree import OOBTree
from BTrees.IOBTree import IOBTree
from AccessControl import getSecurityManager
from zope.i18nmessageid import MessageFactory
from Products.ZCatalog.interfaces import ICatalogBrain
from AccessControl.PermissionRole import rolesForPermissionOn
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager, iszprop
from OFS.PropertyManager import PropertyManager

import logging
log = logging.getLogger('zen.Zuul')

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

def _mergedLocalRoles(object):
    """
    Replacement for Products.CMFCore.utils._mergedLocalRoles, which raises a
    TypeError in certain situations.
    """
    merged = {}
    object = getattr(object, 'aq_inner', object)
    while 1:
        if safe_hasattr(object, '__ac_local_roles__'):
            roles_dict = object.__ac_local_roles__ or {}
            if callable(roles_dict): roles_dict = roles_dict()
            for k, v in roles_dict.items():
                if k in merged:
                    merged[k] += list(v)
                else:
                    merged[k] = list(v)
        if safe_hasattr(object, 'aq_parent'):
            object=object.aq_parent
            object=getattr(object, 'aq_inner', object)
            continue
        if safe_hasattr(object, 'im_self'):
            object=object.im_self
            object=getattr(object, 'aq_inner', object)
            continue
        break

    return deepcopy(merged)


def allowedRolesAndUsers(context):
    allowed = set()
    for r in rolesForPermissionOn("View", context):
        allowed.add(r)
    for user, roles in _mergedLocalRoles(context).iteritems():
        for role in roles:
            if role in allowed:
                allowed.add('user:' + user)
    if 'Owner' in allowed:
        allowed.remove('Owner')
    return list(allowed)


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
        db = getattr(cxn, '_db', None)
        if db and db.database_name != 'temporary':
            app = cxn.root()['Application']
            return app.zport.dmd


_MARKER = object()
def safe_hasattr(object, name):
    return getattr(object, name, _MARKER) is not _MARKER


def unbrain(item):
    if ICatalogBrain.providedBy(item):
        return item.getObject()
    return item


class BrainWhilePossible(object):
    def __init__(self, ob):
        self._ob = ob

    @property
    def _is_brain(self):
        return ICatalogBrain.providedBy(self._ob)

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

    for zprop in filter(iszprop, context.propertyIds()):
        properties[zprop] = PropertyManager.getProperty(context, zprop)
    return properties

def _translateZPropertyValue(zProp, translate, value):
    try:
        return translate(value)
    except Exception, e:
        args = zProp, value, e.__class__.__name__, e
        raise Exception('Unable to translate %s "%s" (%s: %s)' % args)

def getAcquiredZPropertyInfo(obj, zProp, translate=lambda x: x):
    for ancestor in aq_chain(obj)[1:]:
        if isinstance(ancestor, ZenPropertyManager) and ancestor.hasProperty(zProp):
            info = {'ancestor': ancestor.titleOrId()}
            try:
                ancestorValue = getattr(ancestor, zProp)
            except AttributeError:
                log.error("Unable to acquire value for %s", zProp)
                continue
            info['acquiredValue'] = _translateZPropertyValue(zProp, translate, ancestorValue)
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
            zPropInfo['localValue'] = _translateZPropertyValue(zProp, translate, zPropInfo['localValue'])
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
            obj._setProperty(zProp, localValue, type=obj.getPropertyType(zProp))


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


class UncataloguedObjectException(Exception):
    """
    The object we've tried to adapt hasn't been indexed
    """
    def __init__(self, ob):
        self.ob = ob
        log.critical('Object %s has not been catalogued. Skipping.' %
                     ob.getPrimaryUrlPath())


def catalogAwareImap(f, iterable):
    for ob in iterable:
        try:
            yield f(ob)
        except UncataloguedObjectException, e:
            pass


class CatalogLoggingFilter(logging.Filter):

    def filter(self, rec):
        return logging.Filter.filter(self, rec) and not self.matches(rec)

    def matches(self, rec):
        return rec.msg.startswith('uncatalogObject unsuccessfully attempted')



class PathIndexCache(object):
    """
    Cache tree search results for further queries.
    """
    def __init__(self, results, instanceresults=None, relnames=('devices',), treePrefix=None):
        self._brains = IOBTree()
        self._index = OOBTree()
        self._instanceidx = OOBTree()
        self.insert(self._index, results)
        if instanceresults:
            self.insert(self._instanceidx, instanceresults, relnames, treePrefix)

    def insert(self, idx, results, relnames=None, treePrefix=None):
        for brain in results:
            rid = brain.getRID()
            path = brain.getPath()
            if treePrefix and not path.startswith(treePrefix):
                paths = brain.global_catalog._catalog.indexes['path']._unindex[rid]
                for p in paths:
                    if p.startswith(treePrefix):
                        path = p
                        break
            else:
                paths = [path]

            for path in paths:
                path = path.split('/', 3)[-1]
                if relnames:
                    if isinstance(relnames, basestring):
                        relnames = (relnames,)
                    for relname in relnames:
                        path = path.replace('/'+relname, '')
                self._brains[rid] = brain
                for depth in xrange(path.count('/')+1):
                    comp = idx.setdefault(path, IOBTree())
                    comp.setdefault(depth, []).append(rid)
                    path = path.rsplit('/', 1)[0]

    def search(self, path, depth=1):
        path = path.split('/', 3)[-1]
        try:
            idx = self._index[path]
            return map(self._brains.get, idx[depth])
        except KeyError:
            return []

    def count(self, path, depth=None):
        path = path.split('/', 3)[-1]
        try:
            idx = self._instanceidx[path]
            if depth is None:
                depth = max(idx.keys())

            # De-duplicate so we don't repeatedly count the same device in
            # multiple sub-organizers.
            unique_keys = set()
            for d in xrange(depth+1):
                if d not in idx.keys(): continue
                for key in idx[d]:
                    unique_keys.add(key)

            return len(unique_keys)
        except KeyError:
            return 0

    @classmethod
    def test(self, dmd):
        from Products.Zuul.interfaces import ICatalogTool
        results = ICatalogTool(dmd.Devices).search('Products.ZenModel.DeviceOrganizer.DeviceOrganizer')
        instances = ICatalogTool(dmd.Devices).search('Products.ZenModel.Device.Device')
        tree = PathIndexCache(results, instances, 'devices')
