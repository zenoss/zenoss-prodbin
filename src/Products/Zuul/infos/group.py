##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implements
from Products.Zuul.interfaces import IInfo
from Products.Zuul.infos import InfoBase, ProxyProperty

class GroupInfo(InfoBase):
    """
    Takes a zep event and maps it to the format that the UI expects
    """
    implements(IInfo)

    @property
    def members(self):
        pfnMembers = None
        if getattr(self, "_obj"):
            pfnMembers = getattr(self._obj, "getMemberUserIds", None)
        if pfnMembers:
            return pfnMembers()
