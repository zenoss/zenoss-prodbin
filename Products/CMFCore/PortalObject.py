##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" PortalObject: The portal root object class

$Id: PortalObject.py 36457 2004-08-12 15:07:44Z jens $
"""

from Globals import InitializeClass

from PortalFolder import PortalFolder
from Skinnable import SkinnableObjectManager
from permissions import AddPortalMember
from permissions import SetOwnPassword
from permissions import SetOwnProperties
from permissions import MailForgottenPassword
from permissions import RequestReview
from permissions import ReviewPortalContent
from permissions import AccessFuturePortalContent

PORTAL_SKINS_TOOL_ID = 'portal_skins'


class PortalObjectBase(PortalFolder, SkinnableObjectManager):

    meta_type = 'Portal Site'
    _isPortalRoot = 1

    # Ensure certain attributes come from the correct base class.
    __getattr__ = SkinnableObjectManager.__getattr__
    __of__ = SkinnableObjectManager.__of__
    _checkId = SkinnableObjectManager._checkId

    # Ensure all necessary permissions exist.
    __ac_permissions__ = (
        (AddPortalMember, ()),
        (SetOwnPassword, ()),
        (SetOwnProperties, ()),
        (MailForgottenPassword, ()),
        (RequestReview, ()),
        (ReviewPortalContent, ()),
        (AccessFuturePortalContent, ()),
        )

    def getSkinsFolderName(self):
        return PORTAL_SKINS_TOOL_ID

InitializeClass(PortalObjectBase)
