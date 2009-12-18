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
from zope.component.interfaces import IObjectEvent


class IIndexableWrapper(Interface):
    """
    Wraps IGloballyIndexed objects to provide attrs for the catalog to index.
    """


class IGloballyIndexed(Interface):
    """
    Marker interface for objects indexed by the global_catalog.
    """


class ITreeSpanningComponent(Interface):
    """
    Components that place devices in other trees via non-contained relationship.
    """
    def device():
        """
        Return the device associated with this component.
        """


class IIndexingEvent(IObjectEvent):
    """
    An event causing the object to be indexed.
    """
    idxs = Attribute("The names of the indices to be reindexed")
    update_metadata = Attribute("Whether to update the metadata of the object")


class IPathReporter(Interface):
    """
    An adapter that reports the paths under which an object can live, including
    non-containment paths.
    """
    def getPaths():
        """
        Return all paths by which this object may be found.
        """

