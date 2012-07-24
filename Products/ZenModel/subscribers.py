##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenModel.IpInterface import IpInterface, beforeDeleteIpInterface
from OFS.interfaces import IObjectWillBeAddedEvent
from zope.container.interfaces import IObjectRemovedEvent

def unindexBeforeDelete(ob, event):
    """
    Multisubscriber for IIndexed + IObjectWillBeMovedEvent
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        if isinstance(ob, IpInterface):
            beforeDeleteIpInterface(ob, event)
        else:
            ob.unindex_object()

def indexAfterAddOrMove(ob, event):
    """
    Multisubscriber for IIndexed + IObjectMovedEvent.
    """
    if not IObjectRemovedEvent.providedBy(event):
        ob.index_object()
