##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
from BTrees.OOBTree import OOBTree

class AddAccountLocker(Migrate.Step):
    """
    Add attribute to store bad authentication attempts. Extend existing menu to 
    have a possibility to unlock account.
    """

    version = Migrate.Version(5,1,2)

    def cutover(self, dmd):
        
        # Adding attribute if it is not in the place.
        if not hasattr(dmd.zport.acl_users.sessionAuthHelper, 'attempt'):
            dmd.zport.acl_users.attempt = OOBTree()

        if not hasattr(dmd.zenMenus.User_list.zenMenuItems, 'unlockUser'):
            dmd.zenMenus.User_list.manage_addZenMenuItem(id="unlockUser", description='Unlock Users...', action='dialog_unlockUsers', permissions=('Manage DMD',), isdialog=True)
         
            
AddAccountLocker()
