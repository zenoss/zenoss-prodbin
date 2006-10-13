##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
OFS event definitions.

$Id: OFS_event.py 61205 2005-11-02 15:18:34Z efge $
"""

from zope.interface import implements
from zope.app.event.objectevent import ObjectEvent
import OFS_interfaces

class ObjectWillBeMovedEvent(ObjectEvent):
    """An object will be moved."""
    implements(OFS_interfaces.IObjectWillBeMovedEvent)

    def __init__(self, object, oldParent, oldName, newParent, newName):
        ObjectEvent.__init__(self, object)
        self.oldParent = oldParent
        self.oldName = oldName
        self.newParent = newParent
        self.newName = newName

class ObjectWillBeAddedEvent(ObjectWillBeMovedEvent):
    """An object will be added to a container."""
    implements(OFS_interfaces.IObjectWillBeAddedEvent)

    def __init__(self, object, newParent=None, newName=None):
        #if newParent is None:
        #    newParent = object.__parent__
        #if newName is None:
        #    newName = object.__name__
        ObjectWillBeMovedEvent.__init__(self, object, None, None,
                                        newParent, newName)

class ObjectWillBeRemovedEvent(ObjectWillBeMovedEvent):
    """An object will be removed from a container."""
    implements(OFS_interfaces.IObjectWillBeRemovedEvent)

    def __init__(self, object, oldParent=None, oldName=None):
        #if oldParent is None:
        #    oldParent = object.__parent__
        #if oldName is None:
        #    oldName = object.__name__
        ObjectWillBeMovedEvent.__init__(self, object, oldParent, oldName,
                                        None, None)

class ObjectClonedEvent(ObjectEvent):
    """An object has been cloned into a container."""
    implements(OFS_interfaces.IObjectClonedEvent)
