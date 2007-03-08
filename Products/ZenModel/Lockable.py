from Products.ZenRelations import RelationshipBase

UNLOCKED = 0
DELETE_LOCKED = 1
UPDATE_LOCKED = 2

class Lockable:
    
    sendEventOnBlockFlag = False
    modelerLock = UNLOCKED
    
    def getNextLockableParent(obj):
        if obj.getPrimaryNode():
            if isinstance(obj.getPrimaryNode(), Lockable):
                return obj.getPrimaryNode()
            else:
                return getLockableParent(self.getPrimaryParent())
        else:
            return None
        
    def sendEventOnBlock(self):
        if sendEventOnBlockFlag:
            return True
        else:
            return getNextLockableParent(self).sendEventOnBlock()

    def isLockedFromDeletion(self):
        if self.modelerLock == DELETE_LOCKED or self.modelerLock == UPDATE_LOCKED:
            return True
        else:
            return getNextLockableParent(self).isLockedFromDeletion()
    
    def isLockedFromUpdates(self):
        if self.modelerLock == UPDATE_LOCKED: 
            return True
        else:
            return getNextLockableParent(self).isLockedFromUpdates()
    
    def unlock(self):
        self.modelerLock = UNLOCKED
    
    def lockFromDeletion(self):
        self.modelerLock = DELETE_LOCKED
    
    def lockFromUpdates(self):
        self.modelerLock = UPDATE_LOCKED
    
    def lockStatus(self):
        '''
        if self.modelerLock == DELETE_LOCKED:
            return "Locked from deletion"
        elif self.modelerLock == UPDATE_LOCKED:
            return "Locked from updates and deletion"
        elif isinstance(self.getPrimaryParent(), Lockable):
            return "%s by parent" % self.getPrimaryParent().lockStatus()
        elif self.modelerLock == UNLOCKED:
            return "Unlocked"
        '''
        if self.isLockedFromDeletion():
            return "Locked from deletion"
        elif self.isLockedFromUpdates():
            return "Locked from updates and deletion"
        else:
            return "Unlocked"
            
    def lockWarning(self):
        if self.sendEventOnBlock():
            return "Send event on block"
        else:
            return "Do not send event on block"
            