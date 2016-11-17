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
from .interfaces import IProdStateManager, ProdStateNotSetError

from Acquisition import aq_base
from BTrees.OOBTree import OOBTree
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Persistence import Persistent

PRODSTATE_TABLE_PATH = '/zport/dmd/prodstate_table'

class ProdState(Persistent):
    def __init__(self, state=None, premwstate=None):
        self.productionState = state
        self.preMWProductionState = premwstate

class ProdStateManager(object):
    implements(IProdStateManager)
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

    def getProductionState(self, obj):
        guid = IGlobalIdentifier(obj).getGUID()
        try:
            return self.getProductionStateFromGUID(guid)
        except ProdStateNotSetError:
            # Migrate the object's prod state and try again, in case this is
            # a pre-migrate scenario
            self.migrateObject(obj)
            return self.getProductionStateFromGUID(guid)

    def getProductionStateFromGUID(self, guid):
        pstate = self._getProdStatesFromTable(guid).productionState
        if pstate is None:
            raise ProdStateNotSetError
        return pstate

    def getPreMWProductionState(self, obj):
        guid = IGlobalIdentifier(obj).getGUID()
        pstate = self._getProdStatesFromTable(guid).preMWProductionState
        if pstate is None:
            # Migrate the object's prod state and try again, in case this is
            # a pre-migrate scenario
            self.migrateObject(obj)
            pstate = self._getProdStatesFromTable(guid).preMWProductionState
            if pstate is None:
                # Nope, really not there
                raise ProdStateNotSetError
        return pstate

    def setProductionState(self, obj, value):
        guid = IGlobalIdentifier(obj).getGUID()
        pstate = self._getProdStatesFromTable(guid)
        pstate.productionState = value
        self.table[guid] = pstate

    def setPreMWProductionState(self, obj, value):
        guid = IGlobalIdentifier(obj).getGUID()
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

    def clearProductionState(self, obj):
        guid = IGlobalIdentifier(obj).getGUID()
        if guid in self.table:
            del self.table[guid]

    def migrateObject(self, obj):
        """
        Migrate an object's production states from object attributes to the
        central btree.
        """
        obj_unwrapped = aq_base(obj)
        if hasattr(obj_unwrapped, 'productionState'):
            self.setProductionState(obj, obj_unwrapped.productionState)
            del obj_unwrapped.productionState
        if hasattr(obj_unwrapped, 'preMWProductionState'):
            self.setPreMWProductionState(obj, obj_unwrapped.preMWProductionState)
            del obj_unwrapped.preMWProductionState
