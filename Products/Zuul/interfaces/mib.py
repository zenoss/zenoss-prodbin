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

from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode
from info import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IMibFacade(IFacade):

    def addMibPackage(self, package, organizer):
        """
        Add a MIB through whatever package type.
        Currently supports: tar, gzip, compress, URL
        """

    def getInfo(nodeId):
        """
        Get the MIBs tree by a mibTreeNodeId.
        """

    def moveMIBs(sourceUids, targetUid):
        """
        Move MIBOrganizers and MIBClasses uniquely identified by the
        sourceUids parameter to the MIBOrganizer uniquely identified by
        the targetUid parameter.
        """


class IMibOrganizerNode(ITreeNode):
    """
    Marker interface for providing a MIB organizer node in a MIB tree.
    """


class IMibNode(ITreeNode):
    """
    Marker interface for providing a MIB node in a MIB tree.
    """


class IMibEntity(Interface):
    """
    Marker interface for MIBClass and MIBOrganizer
    """


class IMibInfo(IInfo):
    """
    Represents a single MIB instance.
    """
    newId = schema.Text(title=_t(u'Name'),
                        xtype="idfield",
                        required=True,
                        description=_t(u'The name of this MIB'))
    language = schema.Text(title=_t(u'Language'),
                           description=_t(u'Language of this MIB'))
    contact = schema.TextLine(title=_t(u'Contact'),
                           description=_t(u'Contact Info for this MIB'))
    description = schema.TextLine(title=_t(u'Description'),
                           description=_t(u'Description of this MIB'))


class IMibOrganizerInfo(IInfo):
    """
    Represents a single MibOrganizer instance.
    """
    name = Attribute('The name of the MIB')
    description = Attribute('A description of the MIB')
