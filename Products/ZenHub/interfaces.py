###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.component.interfaces import IObjectEvent
from zope.interface import Attribute


class IInvalidationEvent(IObjectEvent):
    """
    ZenHub has noticed an invalidation.
    """
    oid = Attribute("OID of the changed object")


class IUpdateEvent(IInvalidationEvent):
    """
    An object has been updated.
    """


class IDeletionEvent(IInvalidationEvent):
    """
    An object has been deleted.
    """
