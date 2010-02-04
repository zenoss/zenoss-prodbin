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
        return self._getDeviceClassPath('.')
        
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
