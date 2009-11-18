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

from itertools import imap
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceClassFacade, IDeviceClassNode
from Products.Zuul.interfaces import IDeviceClassInfo, IDeviceClass, ITreeFacade
from Products.Zuul.interfaces import ISerializableFactory, IDeviceClass


class DeviceClassNode(TreeNode):
    implements(IDeviceClassNode)
    adapts(IDeviceClass)

    @property
    def id(self):
        path = self._object.getPrimaryUrlPath()[:3]
        return '/'.join(path)

    @property
    def children(self):
        return imap(ITreeNode, self._object.objectValues(spec='DeviceClass'))

    # Everything is potentially a branch, just some have no children.
    leaf = False


class DeviceClassInfo(object):
    implements(IDeviceClassInfo)
    adapts(IDeviceClass)

    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object

    @property
    def name(self):
        return self._object.titleOrId()


class SerializableDeviceClassInfoFactory(object):
    implements(ISerializableFactory)
    adapts(IDeviceClassInfo)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return { 'id' : self.context.id,
                 'name': self.context.name
               }


class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """
    implements(IDeviceClassFacade)


