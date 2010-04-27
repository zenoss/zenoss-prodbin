###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from info import IInfo
from zope.interface import Attribute

class IOrganizerInfo(IInfo):
    """
    Organizer info
    """

class ILocationOrganizerInfo(IOrganizerInfo):
    """
    Location info
    """
    address = Attribute('The address of the organizer')