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

from Products.Zuul.infos import InfoBase

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
        deviceClass = self._getDeviceClassPath('.')
        return '%s.%s' % (template, deviceClass)
        
    @property
    def text(self):
        return self._getDeviceClassPath('/')

    @property
    def leaf(self):
        return True

    def _getDeviceClassPath(self, separator):
        deviceClass = self._object.deviceClass()
        path = deviceClass.getPrimaryPath()
        return separator.join(path[3:])

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

    @property
    def severity(self):
        return self._object.getSeverityString()

    @property
    def enabled(self):
        return self._object.enabled

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
