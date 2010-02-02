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
from zope.interface import Attribute
from Products.Zuul.interfaces import IMarshallable

class IInfo(IMarshallable):
    id = Attribute("Identifier of the represented object (usually path)")
    name = Attribute("Name of the represented object")
    uid = Attribute("The path in the object graph to the object")

