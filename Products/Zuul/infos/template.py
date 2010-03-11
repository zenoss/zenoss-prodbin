###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Acquisition import aq_parent
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.utils import severityId

class TemplateNode(InfoBase):
    
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
    def children(self):
        def caseInsensitive(x, y):
            return cmp(x.text.lower(), y.text.lower())
        self._children.sort(caseInsensitive)
        return self._children

    def _addChild(self, leaf):
        self._children.append(leaf)

class TemplateLeaf(InfoBase):

    def __init__(self, template):
        self._object = template

    @property
    def id(self):
        template = self._object.id
        parent = self._getParentPath('.')
        return '%s.%s' % (template, parent)
        
    @property
    def text(self):
        return self._getParentPath('/')

    @property
    def leaf(self):
        return True

    def _getParentPath(self, separator):
        obj = self._object.deviceClass()
        if obj is None:
            # this template is in a Device
            obj = aq_parent(self._object)
            path = list( obj.getPrimaryPath() )
            # remove the "devices" relationship
            path.pop(-2)
        else:
            # this template is in a DeviceClass.rrdTemplates relationship
            path = list( obj.getPrimaryPath() )
        parts = path[4:-1]
        parts.append(obj.titleOrId())
        return separator + separator.join(parts)

class DataSourceInfo(InfoBase):

    def __init__(self, dataSource):
        self._object = dataSource

    @property
    def id(self):
        return '/'.join( self._object.getPrimaryPath() )

    @property
    def name(self):
        return self._object.getId()
        
    @property
    def source(self):
        return self._object.getDescription()

    @property
    def enabled(self):
        return self._object.enabled

    @property
    def type(self):
        return self._object.sourcetype

class DataPointInfo(InfoBase):

    def __init__(self, dataPoint):
        self._object = dataPoint

    @property
    def id(self):
        return '/'.join( self._object.getPrimaryPath() )

    @property
    def name(self):
        return self._object.getId()

    @property
    def type(self):
        return self._object.rrdtype

    @property
    def leaf(self):
        return True

class ThresholdInfo(InfoBase):

    def __init__(self, threshold):
        self._object = threshold

    @property
    def id(self):
        return '/'.join( self._object.getPrimaryPath() )

    @property
    def name(self):
        return self._object.getId()

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
            # strip out the empty chars (junk our ItemSelector gives us sometimes)
            value = [name for name in value.split(',') if name]
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
        return self._object.getSeverityString()
    
    severity = property(_getSeverity, _setSeverity)

    enabled = ProxyProperty("enabled")

    
class MinMaxThresholdInfo(ThresholdInfo):
    minval = ProxyProperty("minval")
    maxval = ProxyProperty("maxval")
    eventClass = ProxyProperty("eventClass")
    escalateCount = ProxyProperty("escalateCount")
    
            
class GraphInfo(InfoBase):

    def __init__(self, graph):
        self._object = graph

    @property
    def id(self):
        return self._object.getId()

    @property
    def graphPoints(self):
        return self._object.getGraphPointNamesString()

    @property
    def units(self):
        return self._object.units

    @property
    def height(self):
        return self._object.height

    @property
    def width(self):
        return self._object.width
