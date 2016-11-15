##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.component import adapter
from .interfaces import IProdStateManager
from ..guid.interfaces import IGUIDEvent, IGloballyIdentifiable

@adapter(IGloballyIdentifiable, IGUIDEvent)
def updateGUIDToProdStateMapping(object, event):
    mgr = IProdStateManager(object)
    if event.old and event.old != event.new:
        mgr.updateGUID(event.old, event.new)
