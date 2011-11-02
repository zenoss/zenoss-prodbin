###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ManagedEntity

$Id: DeviceComponent.py,v 1.1 2004/04/06 21:05:03 edahl Exp $"""

import logging
log = logging.getLogger("zen.DeviceComponent")

from ZenModelRM import ZenModelRM
from DeviceResultInt import DeviceResultInt
from RRDView import RRDView
from EventView import EventView
from zope.event import notify
from Products.Zuul.catalog.events import IndexingEvent

from Products.ZenRelations.RelSchema import *
from .ZenossSecurity import *
from AccessControl import ClassSecurityInfo
from Products.ZenWidgets.interfaces import IMessageSender

class ManagedEntity(ZenModelRM, DeviceResultInt, EventView, RRDView):
    """
    ManagedEntity is an entity in the system that is managed by it.
    Its basic property is that it can be classified by the ITClass Tree.
    Also has EventView and RRDView available.
    """

    # list of performance multigraphs (see PerformanceView.py)
    # FIXME this needs to go to some new setup and doesn't work now
    #_mgraphs = []

    # primary snmpindex for this managed entity
    snmpindex = 0
    snmpindex_dct = {}
    monitor = True

    _properties = (
     {'id':'snmpindex', 'type':'string', 'mode':'w'},
     {'id':'monitor', 'type':'boolean', 'mode':'w'},
     {'id':'productionState', 'type':'keyedselection', 'mode':'w',
      'select_variable':'getProdStateConversions','setter':'setProdState'},
     {'id':'preMWProductionState', 'type':'keyedselection', 'mode':'w',
      'select_variable':'getProdStateConversions','setter':'setProdState'},
    )

    _relations = (
        ("dependencies", ToMany(ToMany, "Products.ZenModel.ManagedEntity", "dependents")),
        ("dependents", ToMany(ToMany, "Products.ZenModel.ManagedEntity", "dependencies")),
    )

    security = ClassSecurityInfo()
    
    def device(self):
        """Overridden in lower classes if a device relationship exists.
        """
        return None

    def getProductionStateString(self):
        """
        Return the prodstate as a string.

        @rtype: string
        """
        return self.convertProdState(self.productionState)


    security.declareProtected(ZEN_CHANGE_DEVICE_PRODSTATE, 'setProdState')
    def setProdState(self, state, maintWindowChange=False, REQUEST=None):
        """
        Set the device's production state.

        @parameter state: new production state
        @type state: int
        @parameter maintWindowChange: are we resetting state from inside a MW?
        @type maintWindowChange: boolean
        @permission: ZEN_CHANGE_DEVICE
        """
        self.productionState = int(state)
        self.primaryAq().index_object()
        notify(IndexingEvent(self.primaryAq(), ('productionState',), True))
        if not maintWindowChange:
            # Saves our production state for use at the end of the
            # maintenance window.
            self.preMWProductionState = self.productionState

        if REQUEST:
            IMessageSender(self).sendToBrowser(
                "Production State Set",
                "%s's production state was set to %s." % (self.id,
                                      self.getProductionStateString())
            )
            return self.callZenScreen(REQUEST)

