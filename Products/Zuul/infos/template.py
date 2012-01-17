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
from random import random
from zope.interface import implements
from itertools import imap
from Products.Zuul.utils import unbrain, UncataloguedObjectException
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.AdvancedQuery import Eq
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.utils import severityId
from Products.Zuul.interfaces import template as templateInterfaces, ICatalogTool
from Products.Zuul.tree import TreeNode
from Products.Zuul.utils import ZuulMessageFactory as _t


class TemplateInfo(InfoBase):
    description = ProxyProperty('description')
    targetPythonClass = ProxyProperty('targetPythonClass')

    @property
    def definition(self):
        return self._object.getRRDPath()

class TemplateNode(TemplateInfo):

    def __init__(self, template):
        self._object = template
        self._children = []

    @property
    def id(self):
        return self._object.id

    @property
    def text(self):
        return self._object.id

    @property
    def qtip(self):
        return self._object.description

    def _addChild(self, leaf):
        self._children.append(leaf)

    @property
    def hidden(self):
        return False

    def getUIPath(self):
        return self._object.getUIPath()

    @property
    def children(self):
        obj = self._object
        query = Eq('id', obj.id)
        catalog = ICatalogTool(obj.dmd)
        brains = catalog.search(types=RRDTemplate, query=query)
        templates = imap(unbrain, brains)
        for template in templates:
            try:
                yield TemplateLeaf(template)
            except UncataloguedObjectException:
                pass


class TemplateLeaf(TemplateInfo):

    def __init__(self, template):
        self._object = template

    @property
    def id(self):
        templateId = self._object.id
        parent = self._object.getUIPath('.')
        return '%s.%s' % (templateId, parent)

    @property
    def qtip(self):
        return self._object.description

    @property
    def text(self):
        return self._object.getUIPath()

    @property
    def leaf(self):
        return True

    @property
    def children(self):
        return []

    @property
    def hidden(self):
        return False

    @property
    def iconCls(self):
        """
        If we are a component template show the component icon and
        if we are bound show the bound icon
        """
        # component template
        if self._object.targetPythonClass != 'Products.ZenModel.Device':
            return 'tree-template-icon-component'
        # see if it is bound
        deviceClass = self._object.deviceClass()
        # if deviceClass is none it is a device template (and therefore bound)
        if not deviceClass or (self._object.id in deviceClass.getZ('zDeviceTemplates', [])):
            return 'tree-template-icon-bound'
        return 'tree-node-no-icon'


MARKER = object()
def memoize(f):
    def inner(self, *args, **kwargs):
        d = getattr(self._get_cache, '_memo', None)
        if d is None:
            setattr(self._get_cache, '_memo', {})
            d = self._get_cache._memo
        if d.setdefault(self._object, {}).get(f.__name__, MARKER) is MARKER:
            d[self._object][f.__name__] = f(self, *args, **kwargs)
        return d[self._object][f.__name__]
    return inner


class DeviceClassTemplateNode(TreeNode):
    """
    This class is for the "Device class view" of the template tree.
    Keep in mind that on this class "self._object" is actually
    a brains not an object
    """
    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            prefix = '/'.join(self._root.uid.split('/')[:4])
            cache = TreeNode._buildCache(self,
                                         'Products.ZenModel.DeviceClass.DeviceClass',
                                         'Products.ZenModel.RRDTemplate.RRDTemplate',
                                         'rrdTemplates', prefix, orderby='name')
        return cache

    @property
    def id(self):
        """
        We have to make the template paths unique even though the same
        template shows up multiple times.  This is the acquired
        template path.
        NOTE that it relies on the _porganizerPath  being set
        """
        if self.isOrganizer:
            return super(DeviceClassTemplateNode, self).id
        path = self._organizerPath + '/rrdTemplates/' + self._object.name
        return path.replace('/', '.')

    @property
    @memoize
    def qtip(self):
        return self._get_object.description

    @property
    @memoize
    def isOrganizer(self):
        """
        returns True if this node is an organizer
        """
        return self._object.meta_type == 'DeviceClass'

    @property
    def _organizer(self):
        return self if self.isOrganizer else self._parent._get_object

    @property
    @memoize
    def _get_object(self):
        return self._object.getObject()

    @property
    def iconCls(self):
        if self.isOrganizer:
            return ''
        # check to see if it is a component template
        template = self._get_object
        if template.targetPythonClass != 'Products.ZenModel.Device':
            return 'tree-template-icon-component'
        # check to see if it is bound
        organizer = self._organizer
        if template.id in organizer.zDeviceTemplates:
            return 'tree-template-icon-bound'
        return 'tree-node-no-icon'

    @property
    @memoize
    def leaf(self):
        return not self.isOrganizer

    @property
    def text(self):
        """
        If a template display the path otherwise just show what the parent shows
        """
        if self.isOrganizer:
            return self._object.name
        # it is a template
        if self._organizerPath in self.uid:
            path = _t('Locally Defined')
        else:
            path = self._get_object.getUIPath()
        return "%s (%s)" % (self._object.name, path)

    def _get_templates(self):
        idx = self._get_cache._instanceidx
        parts = self.uid.split('/')[3:]
        path = ''
        templates = {}
        brains = self._get_cache._brains
        while parts:
            path = '/'.join((path, parts.pop(0))).lstrip('/')
            rids = idx.get(path, {}).get(1, ())
            for rid in rids:
                brain = brains[rid]
                templates[brain.name] = brain
        return templates.values()

    @property
    @memoize
    def children(self):
        """
        Must return all the device classes as well as templates available at this level (as leafs).
        This will return all templates that are acquired as well.
        """
        if not self.isOrganizer:
            return []
        # get all organizers as brains
        orgs = self._get_cache.search(self.uid)
        templates = self._get_templates()
        path = self.path
        # return them both together
        results = []
        for brain in orgs:
            item = DeviceClassTemplateNode(brain, self._root, self)
            results.append(item)

        for template in templates:
            item = DeviceClassTemplateNode(template, self._root, self)
            item._organizerPath = path
            results.append(item)
        return results



class RRDDataSourceInfo(InfoBase):
    implements(templateInterfaces.IRRDDataSourceInfo)
    """
    This is the default Schema/Info for every class that descends from
    RRDDataSource.  Most of the zenpacks descend from this.
    """
    def __init__(self, dataSource):
        self._object = dataSource

    @property
    def id(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def source(self):
        return self._object.getDescription()

    @property
    def type(self):
        return self._object.sourcetype

    # severity
    def _setSeverity(self, value):
        try:
            if isinstance(value, str):
                value = severityId(value)
        except ValueError:
            # they entered junk somehow (default to info if invalid)
            value = severityId('info')
        self._object.severity = value

    def _getSeverity(self):
        return self._object.getSeverityString()

    @property
    def newId(self):
        return self._object.id

    severity = property(_getSeverity, _setSeverity)
    enabled = ProxyProperty('enabled')
    component = ProxyProperty('component')
    eventClass = ProxyProperty('eventClass')
    eventKey = ProxyProperty('eventKey')


class BasicDataSourceInfo(InfoBase):
    """
    Not really used but SNMPDataSource and CommandDataSource both
    share common properties so I am using this subclass
    """
    def __init__(self, dataSource):
        self._object = dataSource

    @property
    def testable(self):
        """
        This tells the client if we can test this datasource against a
        specific device.  It defaults to True and expects subclasses
        to overide it if they can not
        """
        return True

    @property
    def id(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def source(self):
        return self._object.getDescription()

    @property
    def type(self):
        return self._object.sourcetype

    enabled = ProxyProperty('enabled')

    @property
    def availableParsers(self):
        """
        returns a list of all available parsers
        """
        if hasattr(self._object, 'parsers'):
            return self._object.parsers()
        return []

    # severity
    def _setSeverity(self, value):
        try:
            if isinstance(value, str):
                value = severityId(value)
        except ValueError:
            # they entered junk somehow (default to info if invalid)
            value = severityId('info')
        self._object.severity = value

    def _getSeverity(self):
        return self._object.severity

    @property
    def newId(self):
        return self._object.id

    severity = property(_getSeverity, _setSeverity)
    cycletime = ProxyProperty('cycletime')
    eventClass = ProxyProperty('eventClass')


class SNMPDataSourceInfo(BasicDataSourceInfo):
    implements(templateInterfaces.ISNMPDataSourceInfo)
    """
    DataSource for SNMP (Basic DataSource with a type of 'SNMP')
    """
    oid = ProxyProperty('oid')


class CommandDataSourceInfo(BasicDataSourceInfo):
    implements(templateInterfaces.ICommandDataSourceInfo)
    """
    Datasource for Commands (Basic DataSource with a type of 'COMMAND')
    """
    parser = ProxyProperty('parser')
    usessh = ProxyProperty('usessh')
    component = ProxyProperty('component')
    eventKey = ProxyProperty('eventKey')
    commandTemplate = ProxyProperty('commandTemplate')


class PingDataSourceInfo(RRDDataSourceInfo):
    implements(templateInterfaces.IPingDataSourceInfo)
    """
    DataSource for PING
    """
    cycleTime = ProxyProperty('cycleTime')
    attempts = ProxyProperty('attempts')
    sampleSize = ProxyProperty('sampleSize')


class DataPointInfo(InfoBase):
    implements(templateInterfaces.IDataPointInfo)

    def __init__(self, dataPoint):
        self._object = dataPoint

    description = ProxyProperty('description')

    @property
    def name(self):
        return "%s.%s" % (self._object.datasource().titleOrId(),
                          self._object.titleOrId())

    @property
    def id(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def type(self):
        return self._object.rrdtype

    @property
    def newId(self):
        return self._object.id

    # alias
    def _setAliases(self, value):
        """
        Receives a list of Dictionaries of the form
        [{ 'id': id, 'formula': formula}] Each dictionary
        will form a new Alias
        """
        # get and remove all existing aliases
        for alias in self._getAliases():
            self._object.removeAlias(alias.name)

        # add each alias
        for alias in value:
            if 'id' in alias and 'formula' in alias and alias['id']:
                self._object.addAlias(alias['id'], alias['formula'])

    def _getAliases(self):
        """
        Returns a generator of all the DataAliases
        associated with this DataPoint
        """
        aliases = []
        for alias in self._object.aliases():
            aliases.append(templateInterfaces.IDataPointAlias(alias))

        return aliases

    aliases = property(_getAliases, _setAliases)

    @property
    def leaf(self):
        return True

    @property
    def availableRRDTypes(self):
        """
        Returns a list of all valid RRD Types. This is used as the
        store for which this particular object's rrdtype is selected
        """
        return self._object.rrdtypes

    rrdtype = ProxyProperty('rrdtype')
    createCmd = ProxyProperty('createCmd')
    isrow = ProxyProperty('isrow')
    rrdmin = ProxyProperty('rrdmin')
    rrdmax = ProxyProperty('rrdmax')


class DataPointAliasInfo(InfoBase):
    implements(templateInterfaces.IDataPointAlias)
    """
    """
    @property
    def id(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def name(self):
        return self._object.getId()

    @property
    def formula(self):
        return self._object.formula


class ThresholdInfo(InfoBase):
    implements(templateInterfaces.IThresholdInfo)

    def __init__(self, threshold):
        self._object = threshold

    @property
    def id(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def newId(self):
        return self._object.id

    @property
    def type(self):
        return self._object.getTypeName()

    @property
    def dataPoints(self):
        return self._object.getDataPointNamesString()

    # dsnames
    def _setDsnames(self, value):
        """
        dsnames can be either a list of valid names or a comma separated string
        """
        if value and isinstance(value, str):
            # strip out the empty chars
            value = [name.strip() for name in value.split(',') if name]
        self._object.dsnames = value

    def _getDsnames(self):
        return self._object.dsnames

    dsnames = property(_getDsnames, _setDsnames)

    # severity
    def _setSeverity(self, value):
        try:
            if isinstance(value, str):
                value = severityId(value)
        except ValueError:
            # they entered junk somehow (default to info if invalid)
            value = severityId('info')
        self._object.severity = value

    def _getSeverity(self):
        return self._object.severity

    severity = property(_getSeverity, _setSeverity)

    enabled = ProxyProperty("enabled")

    eventClass = ProxyProperty("eventClass")

class MinMaxThresholdInfo(ThresholdInfo):
    implements(templateInterfaces.IMinMaxThresholdInfo)
    minval = ProxyProperty("minval")
    maxval = ProxyProperty("maxval")
    escalateCount = ProxyProperty("escalateCount")


class GraphInfo(InfoBase):

    def __init__(self, graph):
        self._object = graph

    @property
    def id(self):
        return self._object.getId()

    @property
    def newId(self):
        return self._object.id

    @property
    def graphPoints(self):
        return self._object.getGraphPointNamesString()

    custom = ProxyProperty('custom')
    height = ProxyProperty('height')
    width = ProxyProperty('width')
    units = ProxyProperty('units')
    log = ProxyProperty('log')
    base = ProxyProperty('base')
    miny = ProxyProperty('miny')
    maxy = ProxyProperty('maxy')
    hasSummary = ProxyProperty('hasSummary')
    sequence = ProxyProperty('sequence')

    @property
    def rrdVariables(self):
        """
        Returns a list of RRD variables
        """
        return self._object.getRRDVariables()

    @property
    def fakeGraphCommands(self):
        """
        Used to display the graph commands to the user
        """
        return self._object.getFakeGraphCmds()
