##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from exceptions import Exception
from zope.interface import Interface

class IProdStateManager(Interface):
    """
    A utility that can register and look up production states for objects.
    """
    def getProductionState(object):
        """
        Return the current production state of the object.
        """
    def getPreMWProductionState(object):
        """
        Return the pre-maintenance window state of the object.
        """
    def setProductionState(object, value):
        """
        Set the current production state of the object.
        """
    def setPreMWProductionState(object, value):
        """
        Set the pre-maintenance window state of the object.
        """
    def updateGUID(oldGUID, newGUID):
        """
        Handle the situation where an object's guid has changed or the
        object has been removed
        """