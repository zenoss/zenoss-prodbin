###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface, Attribute

class ITrackedAction(Interface):
    """
    Any action that can be tracked.
    """


class IUserAction(ITrackedAction):
    """
    Any action performed by a user that can be tracked.
    The current user will be determined automatically.
    """
    actionCategory = Attribute("Category of the action.")
    actionName = Attribute("Name of the action.")
    extra = Attribute("Dictionary of any other parameters.")
