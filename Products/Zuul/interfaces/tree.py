###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Interface, Attribute

from Products.Zuul.interfaces import IMarshallable


class ITreeNode(IMarshallable):
    """
    Represents a single branch or leaf in a tree.
    """
    path = Attribute("The path of the node, e.g. Processes/Apache/httpd")
    id = Attribute('The unique ID of the node, e.g. /zport/dmd/Processes')
    text = Attribute('The text label that represents the node')
    children = Attribute("The node's children")
    leaf = Attribute('Is this node a leaf (incapable of having children)')


class ITreeFacade(Interface):
    """
    Exposes methods for working with tree hierarchies.
    """
    def getTree(root):
        """
        Get the tree of instances.

        Returns the node identified by C{root}, which can be walked using the
        C{children} attribute.
        """


class ICatalogTool(Interface):
    """
    Accesses the global catalog to pull objects of a certain type.
    """
    def search(types=(), start=0, limit=None, orderby='name',
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None):
        """
        Build and execute a query against the global catalog.
        """
    def getBrain(path):
        """
        Gets the brain representing the object defined at C{path}.
        """
    def parents(path):
        """
        Get brains representing parents of C{path} + C{path}. Good for making
        breadcrumbs without waking up all the actual parent objects.
        """
    def count(types, path):
        """
        Get the count of children matching C{types} under C{path}.

        This is cheap; the lazy list returned from a catalog search knows its
        own length without exhausting its contents.

        @param types: Classes or interfaces that should be matched
        @type types: tuple
        @param path: The path under which children should be counted. Defaults
        to the path of C{self.context}.
        @type path: str
        @return: The number of children matching.
        @rtype: int
        """
    def update(obj):
        """
        Update the metadata for an object. Note: does NOT reindex.
        """

