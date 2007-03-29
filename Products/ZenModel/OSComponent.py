#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

from ManagedEntity import ManagedEntity
from DeviceComponent import DeviceComponent


class OSComponent(DeviceComponent, ManagedEntity):
    """
    Logical Operating System component like a Process, IpInterface, etc.
    """
    isUserCreatedFlag = False
    
    def setUserCreateFlag(self):
        isUserCreatedFlag = True
        
    def isUserCreated(self):
        return isUserCreatedFlag

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        os = self.os()
        if os: return os.device()

    def manage_deleteComponent(self, REQUEST=None):
        """
        Delete OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url()
        self.getPrimaryParent()._delObject(self.id)
        '''
        eventDict = {
            'eventClass': Change_Remove,
            'device': self.device().id,
            'component': self.id or '',
            'summary': 'Deleted by user: %s' % 'user',
            'severity': Event.Info,
            }
        self.dmd.ZenEventManager.sendEvent(eventDict)
        '''
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)

    def manage_updateComponent(context, datamap, REQUEST=None):
        """
        Update OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url()
        self.getPrimaryParent()._updateObject(self, datamap)
        '''
        eventDict = {
            'eventClass': Change_Set,
            'device': self.device().id,
            'component': self.id or '',
            'summary': 'Updated by user: %s' % 'user',
            'severity': Event.Info,
            }
        self.dmd.ZenEventManager.sendEvent(eventDict)
        '''
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)