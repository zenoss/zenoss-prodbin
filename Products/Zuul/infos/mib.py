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

from itertools import imap, chain

from zope.component import adapts
from zope.interface import implements
from Products.Zuul import getFacade
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.interfaces import IMibInfo, IMibOrganizerNode, IMibNode
from Products.Zuul.interfaces import ICatalogTool, IMibOrganizerInfo
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.MibModule import MibModule
from Products.ZenModel.MibBase import MibBase


class MibOrganizerNode(TreeNode):
    implements(IMibOrganizerNode)
    adapts(MibOrganizer)

    @property
    def text(self):
        text = super(MibOrganizerNode, self).text
        count = ICatalogTool(self._object).count((MibModule,), self.uid)
        return {'text': text, 'count': count}

    @property
    def children(self):
        org = self._object.getObject()
        return chain(imap(MibOrganizerNode, org.children()),
                     imap(MibNode, org.mibs()))

    @property
    def leaf(self):
        return False

    @property
    def iconCls(self):
        return 'folder'

    @property
    def qtip(self):
        return self._object.description
    
class MibNode(TreeNode):
    """
    Nodes or traps are just subclasses of MibBase
    """
    implements(IMibNode)
    adapts(MibBase)

    def __init__(self, obj):
        TreeNode.__init__(self, obj)
        self._nodes = []

    def _addSubNode(self, node):
        self._nodes.append(node)

    @property
    def children(self):
        return self._nodes

    @property
    def text(self):
        obj = self._object.getObject()
        if hasattr(obj, 'oid'):
            return obj.oid + ' ' + self._object.id
        return self._object.id

    @property
    def oid(self):
        obj = self._object.getObject()
        if hasattr(obj, 'oid'):
            return obj.oid
        return ''

    @property
    def leaf(self):
        return len(self._nodes) == 0

    @property
    def iconCls(self):
        if self.leaf:
            return 'leaf'
        return 'folder'

    @property
    def qtip(self):
        return self._object.description
    
class MibInfoBase(InfoBase):
    pass


class MibInfo(MibInfoBase):
    implements(IMibInfo)

    @property
    def count(self):
        return 1

    @property
    def newId(self):
        return self._object.id

    language = ProxyProperty('language')
    contact = ProxyProperty('contact')
    description = ProxyProperty('description')
    
class MibOrganizerInfo(MibInfoBase):
    implements(IMibOrganizerInfo)
    adapts(MibOrganizer)

