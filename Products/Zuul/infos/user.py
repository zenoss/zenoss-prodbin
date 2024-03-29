##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implements
from Products.Zuul.interfaces import IInfo
from Products.Zuul.infos import InfoBase, ProxyProperty

class UserInfo(InfoBase):
    """
    Takes a zep event and maps it to the format that the UI expects
    """
    implements(IInfo)

    email = ProxyProperty('email')
    pager = ProxyProperty('pager')
    dashboardState = ProxyProperty('dashboardState')
    defaultPageSize = ProxyProperty('defaultPageSize')
    userTheme = ProxyProperty('userTheme')
    netMapStartObject = ProxyProperty('netMapStartObject')

    @property
    def groups(self):
        return self._object.getUserGroupSettingsNames()

    @property
    def roles(self):
        return self._object.getUserRoles()

    # TODO: implement editing passwords
