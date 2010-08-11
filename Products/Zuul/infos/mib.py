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
        #cat = ICatalogTool(self._object)
        #orgs = cat.search(MibOrganizer, paths=(self.uid,), depth=1)
        #return catalogAwareImap(MibOrganizerNode, orgs)

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
    implements(IMibNode)
    adapts(MibModule)

    @property
    def text(self):
        return self._object.id

    @property
    def children(self):
        return []

    @property
    def leaf(self):
        return True

    @property
    def iconCls(self):
        return 'leaf'

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


