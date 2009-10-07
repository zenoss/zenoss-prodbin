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
import zope.interface
from interfaces import IExtDirectAPI, IMainSnippetManager
from Products.ZenUI3.utils.javascript import JavaScriptSnippetManager


class MainSnippetManager(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IMainSnippetManager)


class ExtDirectAPI(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IExtDirectAPI)
