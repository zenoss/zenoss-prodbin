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

DEFAULT_PRODUCTION_STATE = 1000

class ProdStateManager(object):
    implements(IProdStateManager)

    def __init__(self, context):
        self.context = context


    def getProductionState(self, object):
        try:
            if object._productionState is None:
                return DEFAULT_PRODUCTION_STATE
        except AttributeError:
            return DEFAULT_PRODUCTION_STATE

        return object._productionState

    def getPreMWProductionState(self, object):
        try:
            if object._preMWProductionState is None:
                return DEFAULT_PRODUCTION_STATE
        except AttributeError:
            return DEFAULT_PRODUCTION_STATE

        return object._preMWProductionState

    def setProductionState(self, object, value):
        object._productionState = value

    def setPreMWProductionState(self, object, value):
        object._preMWProductionState = value
