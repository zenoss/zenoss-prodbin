##############################################################################
#
# Copyright (c) 2004, 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Five interfaces

$Id: interfaces.py 61205 2005-11-02 15:18:34Z efge $
"""
from zope.interface import Interface
from zope.interface.interfaces import IInterface

class IBrowserDefault(Interface):
    """Provide a hook for deciding about the default view for an object"""

    def defaultView(self, request):
        """Return the object to be published
        (usually self) and a sequence of names to traverse to
        find the method to be published.
        """

class IMenuItemType(IInterface):
    """Menu item type

    Menu item types are interfaces that define classes of
    menu items.
    """

#
# BBB: Zope core interfaces for Zope 2.8
#

try:
    import AccessControl.interfaces
    import Acquisition.interfaces
    import App.interfaces
    import OFS.interfaces
    import webdav.interfaces

    def monkey():
        pass

except ImportError:

    def monkey():
        import sys
        from Products.Five.bbb import AccessControl_interfaces
        from Products.Five.bbb import Acquisition_interfaces
        from Products.Five.bbb import App_interfaces
        from Products.Five.bbb import OFS_interfaces
        from Products.Five.bbb import OFS_event
        from Products.Five.bbb import OFS_subscribers
        from Products.Five.bbb import webdav_interfaces

        sys.modules['AccessControl.interfaces'] = AccessControl_interfaces
        sys.modules['Acquisition.interfaces'] = Acquisition_interfaces
        sys.modules['App.interfaces'] = App_interfaces
        sys.modules['OFS.interfaces'] = OFS_interfaces
        sys.modules['OFS.event'] = OFS_event
        sys.modules['OFS.subscribers'] = OFS_subscribers
        sys.modules['webdav.interfaces'] = webdav_interfaces
