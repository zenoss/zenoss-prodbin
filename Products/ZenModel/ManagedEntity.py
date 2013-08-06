##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""ManagedEntity
Objects that may of be interest from a CMDB perspective.
"""

import logging
log = logging.getLogger("zen.DeviceComponent")

from zope.event import notify

from ZenModelRM import ZenModelRM
from DeviceResultInt import DeviceResultInt
from RRDView import RRDView
from EventView import EventView
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenRelations.RelSchema import ToMany, ToManyCont, ToOne
from .ZenossSecurity import ZEN_CHANGE_DEVICE_PRODSTATE
from AccessControl import ClassSecurityInfo
from Products.ZenWidgets.interfaces import IMessageSender
from Products.ZenModel.MaintenanceWindowable import MaintenanceWindowable


class ManagedEntity(ZenModelRM, DeviceResultInt, EventView, RRDView,
                    MaintenanceWindowable):
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
        ("maintenanceWindows",ToManyCont(
            ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
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

    
