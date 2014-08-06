##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from zope.component import adapter
from zope.container.interfaces import IObjectAddedEvent, IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent

from Products.ZenModel.IpInterface import IpInterface, beforeDeleteIpInterface

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

@adapter(IpInterface, IObjectWillBeMovedEvent)
def onInterfaceRemoved(ob, event):
    """
    Unindex
    """

    if not IObjectWillBeAddedEvent.providedBy(event):
        device = ob.device()
        if device:
            macs = device.getMacAddressCache()
            if ob.macaddress in macs:
                macs.remove(ob.macaddress)


@adapter(IpInterface, IObjectAddedEvent)
def onInterfaceAdded(ob, event):
    """
    Simple subscriber that fires the indexing event for all indices.
    """

    if ob.macaddress:
        device = ob.device()
        if device:
            device.getMacAddressCache().add(ob.macaddress)

