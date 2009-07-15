###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate
from OFS.ObjectManager import ObjectManager
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager

def migrateZProps(manager):
    """
    Copy the manager's zProperties from its __dict__ to its _propertyValues
    dictionary. Then do the same recursively for any child 
    ZenPropertyManagers.
    """
    manager._p_changed = True
    for id in vars(manager).keys():
        # PropertyDescriptor moves the value from __dict__ to
        # _propertyValues when getattr is called
        getattr(manager, id)
    if isinstance(manager, ObjectManager):
        for ob in manager.objectValues():
            if isinstance(ob, ZenPropertyManager):
                migrateZProps(ob)

class descriptor(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        migrateZProps(dmd.Devices)
        
descriptor()
