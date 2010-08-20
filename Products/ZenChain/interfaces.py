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
from zope.interface import Interface, Attribute


class INestedSetMember(Interface):
    id = Attribute("Identifier of this item")
    parent = Attribute("The parent of this item")
    left = Attribute("Item to the left")
    right = Attribute("Item to the right")


class IMultiTreeNestedSetMember(INestedSetMember):
    category = Attribute("Tree identifier")
