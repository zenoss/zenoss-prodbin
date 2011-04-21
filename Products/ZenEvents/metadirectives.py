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
from zope.interface import Interface
from zope.configuration.fields import GlobalObject

class IEventPluginDirective(Interface):
    """
    Registers an event plugin as a named utility.
    """
    plugin = GlobalObject(
        title=u"Plugin",
        description=u"The class of the plugin to register"
    )

class IPreEventPluginDirective(IEventPluginDirective):
    """
    Registers an event plugin as a named utility.
    """


class IPostEventPluginDirective(IEventPluginDirective):
    """
    Registers an event plugin as a named utility.
    """
