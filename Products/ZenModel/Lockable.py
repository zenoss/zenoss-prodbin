UNLOCKED = 0
DELETE_LOCKED = 1
UPDATE_LOCKED = 2

class Lockable:
    
    sendEventOnBlock = False
    modelerLock = UNLOCKED
    
    def isLockedFromDelete(self):
        if self.modelerLock == DELETE_LOCKED or self.modelerLock == UPDATE_LOCKED:
            return True
        elif isinstance(self.getPrimaryParent(), Lockable):
            return self.getPrimaryParent().isLockedFromDelete()
        else:
            return False
    
    def isLockedFromUpdate(self):
        if self.modelerLock == UPDATE_LOCKED: 
            return True
        elif isinstance(self.getPrimaryParent(), Lockable):
            return self.getPrimaryParent().isLockedFromUpdate()
        else:
            return False
    
    def unlock(self):
        self.modelerLock = UNLOCKED
    
    def lockFromDeletion(self):
        self.modelerLock = DELETE_LOCKED
    
    def lockFromUpdate(self):
        self.modelerLock = UPDATE_LOCKED
    
    def lockStatus(self):
        if self.modelerLock == DELETE_LOCKED:
            return "Locked from deletion"
        elif self.modelerLock == UPDATE_LOCKED:
            return "Locked from updates and deletion"
        elif isinstance(self.getPrimaryParent(), Lockable):
            return "%s by parent" % self.getPrimaryParent().lockStatus()
        elif self.modelerLock == UNLOCKED:
            return "Unlocked"
        
    def lockWarning(self):
        if self.sendEventOnBlock:
            return "Send event on block"
        else:
            return "Do not send event on block"
            