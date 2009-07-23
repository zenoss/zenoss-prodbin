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

"""
Utilities to help with migration scripts.
"""

from OFS.ObjectManager import ObjectManager
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.ZenRelations.ZenPropertyManager import PropertyDescriptor

def migratePropertyType(manager, id, type):
    """
    Change the type of the property with the specified id to the specified
    type on this manager (a ZenPropertyManager instance, typically an instance
    of DeviceClass or Device) and recursively for any child managers. The 
    value is transformed using the appropriate transformers (the get
    transformer for the old type and the set transformer for the new type).
    """
    if manager.hasProperty(id):
        value = manager.getProperty(id)
        manager._delProperty(id)
        setattr(ZenPropertyManager, id, PropertyDescriptor(id, type))
        manager._setProperty(id, value, type)
    if isinstance(manager, ObjectManager):
        for ob in manager.objectValues():
            if isinstance(ob, ZenPropertyManager):
                migratePropertyType(ob, id, type)
                
