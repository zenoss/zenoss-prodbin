#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *


class ZenPackable:
    "mix-in allows an object to be referenced by a ZenPack"

    meta_type = "ZenPackable"

    _relations = (
        ("pack", ToOne(ToMany, "ZenPack", "packables")),
    )
