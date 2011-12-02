###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Operations for Settings.

Available at:  /zport/dmd/settings_router
"""
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import require
from Products import Zuul
from Products.ZenMessaging.audit import audit


class SettingsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on settings
    """

    def _getUISettings(self):
        return self.context.zport.dmd.UserInterfaceSettings

    def getUserInterfaceSettings(self):
        """
        Retrieves the collection of User interface settings
        """
        settings = self._getUISettings()
        return DirectResponse.succeed(data=Zuul.marshal(settings.getSettingsData()))

    @require('Manage DMD')
    def setUserInterfaceSettings(self, **kwargs):
        """
        Accepts key value pair of user interface settings.
        """
        settings = self._getUISettings()
        oldValues = {}
        newValues = {}
        for key, value in kwargs.iteritems():
            oldValues[key] = str(getattr(settings, key, None))
            newValues[key] = str(value)
            setattr(settings, key, value)
        audit('UI.InterfaceSettings.Edit', data_=newValues, oldData_=oldValues)
        return DirectResponse.succeed()
