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

from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode
from info import IInfo

class IServiceFacade(IFacade):

    def getInfo(nodeId):
        """
        Get the Services tree by a serviceTreeNodeId.
        """

class IServiceNode(ITreeNode):
    """
    Marker interface for providing a Service node in a Service tree.
    """
class IServiceOrganizerNode(ITreeNode):
    """
    Marker interface for providing a Service node in a Service tree.
    """

class IServiceEntity(Interface):
    """
    Marker interface for ServiceClass and ServiceOrganizer
    """

class IServiceInfo(IInfo):
    """
    Represents a single ServiceClass instance.
    """
    name = Attribute('The name of the service')
    description = Attribute('A description of the service')
    serviceKeys = Attribute('Keys which will match for defining services.')
    port = Attribute('The port that the service runs on')
    count = Attribute('The number of instances.')

class IServiceOrganizerInfo(IInfo):
    """
    Represents a single ServiceOrganizer instance.
    """
    name = Attribute('The name of the service')
    description = Attribute('A description of the service')

