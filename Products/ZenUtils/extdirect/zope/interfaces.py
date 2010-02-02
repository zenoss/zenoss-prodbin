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
from zope.interface import Interface
from zope.viewlet.interfaces import IViewletManager

class IExtDirectJavaScriptManager(IViewletManager):
    """
    A viewlet manager to register API providers.
    """

class IExtDirectJavaScriptAndSourceManager(IExtDirectJavaScriptManager):
    """
    A viewlet manager to publish Ext javascript resources and register API
    providers.
    """

class IDirectProviderDefinition(Interface):
    def render():
        """
        Generate client-side stub defining a provider.
        """
