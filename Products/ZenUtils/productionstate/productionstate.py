##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""productionState

Keep track of the current and pre-maintenance window production states
for all ManagedEntity objects.
"""
from zope.interface import implements
from .interfaces import IProdStateManager

from BTrees.OOBTree import OOBTree
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

PRODSTATE_TABLE_PATH = '/zport/dmd/prodstate_table'
DEFAULT_PRODUCTION_STATE = 1000

class ProdState(object):
    def __init__(self, state=None, premwstate=None):
        self.productionState = state
        self.preMWProductionState = premwstate

class ProdStateManager(object):
    implements(IProdStateManager)
    _default_state = DEFAULT_PRODUCTION_STATE
    _table_path = PRODSTATE_TABLE_PATH

    def __init__(self, context):
        self.context = context
        
        # Make sure the table exists and create it if not
        self.traverse = self.context.unrestrictedTraverse
        try:
            self.table = self.traverse(self._table_path)
        except (AttributeError, KeyError), e:
            parent, name = self._table_path.rsplit('/', 1)
            self.table = OOBTree()
            setattr(self.traverse(parent), name, self.table)
    
    def getProductionState(self, object):
        guid = IGlobalIdentifier(object).getGUID()
        return self.getProductionStateFromGUID(guid)

    def getProductionStateFromGUID(self, guid):
        pstate = self._getProdStatesFromTable(guid).productionState
        if pstate is None:
            return self._default_state
        return pstate

    def getPreMWProductionState(self, object):
        guid = IGlobalIdentifier(object).getGUID()
        pstate = self._getProdStatesFromTable(guid).preMWProductionState
        if pstate is None:
            return self._default_state
        return pstate

    def setProductionState(self, object, value):
        guid = IGlobalIdentifier(object).getGUID()
        pstate = self._getProdStatesFromTable(guid)
        pstate.productionState = value
        self.table[guid] = pstate

    def setPreMWProductionState(self, object, value):
        guid = IGlobalIdentifier(object).getGUID()
        pstate = self._getProdStatesFromTable(guid)
        pstate.preMWProductionState = value
        self.table[guid] = pstate

    def _getProdStatesFromTable(self, guid):
        pstate = self.table.get(guid, None)
        if pstate is None:
            pstate = ProdState()
        return pstate

    # Needed to handle cases where an object is removed or its guid changes
    def updateGUID(self, oldGUID, newGUID):
        if oldGUID in self.table:
            if newGUID:
                self.table[newGUID] = self.table.get(oldGUID)

            del self.table[oldGUID]

