##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Marker interface for callable opaque items with manage_* hooks.

$Id: IOpaqueItems.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class ICallableOpaqueItem(Interface):
    """Interface for callable opaque items.

    Opaque items are subelements that are contained using something that
    is not an ObjectManager.

    On add, copy, move and delete operations a marked opaque items
    'manage_afterAdd', 'manage_afterClone' and 'manage_beforeDelete' hooks
    get called if available. Unavailable hooks do not throw exceptions.
    """

    def __init__(obj, id):
        """Return the opaque item and assign it to 'obj' as attr with 'id'.
        """
    
    def __call__():
        """Return the opaque items value.
        """
    
    def getId():
        """Return the id of the opaque item.
        """

class ICallableOpaqueItemEvents(Interface):
    """CMF specific events upon copying, renaming and deletion.
    """
    def manage_afterClone(item):
        """After clone event hook.
        """
    
    def manage_beforeDelete(item, container):
        """Before delete event hook.
        """
    
    def manage_afterAdd(item, container):
        """After add event hook.
        """
