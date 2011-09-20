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

from zope.interface import implements
from .interfaces import IUserAction

class UserAction(object):
    """Any action performed by a user that can be tracked."""
    implements(IUserAction)

    def __init__(self, actionCategory, actionName=None, extra=None, **kwargs):
        self.actionCategory = actionCategory
        self.actionName = actionName
        if extra is None:
            extra = {}
        extra.update(kwargs)
        self.extra = extra
