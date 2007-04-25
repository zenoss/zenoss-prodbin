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

from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *


class ZenPackable:
    "mix-in allows an object to be referenced by a ZenPack"

    meta_type = "ZenPackable"

    _relations = (
        ("pack", ToOne(ToMany, "Products.ZenModel.ZenPack", "packables")),
    )



