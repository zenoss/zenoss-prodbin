###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals
import zope.interface

from collections import defaultdict
from Products.ZenUtils.Utils import convToUnits

UNAVAILABLE = 'N/A'

def percent(partial, total):
    if partial is None or total is None:
        return None
    if not total:
        return None
    return partial * 100 / total


def percentString(n, decimals=0):
    if n is None:
        return UNAVAILABLE
    return '%*.*f' % (2, decimals, n)


class Record( object ):
    zope.interface.implements( zope.interface.Interface )
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, **kw):
        self.values = kw.copy()

    def __str__(self):
        return str(self.values)


    def __repr__(self):
        return repr(self.values)


    def __getitem__(self, name):
        return self.values[name]

    def __getattr__(self, name):
        return self.values.get(name)

    def percent(self, partial, total):
        return percent(partial, total)

    def percentString(self, n, decimals=0):
        return percentString(n, decimals)

    def humanBytes(self, value, scale=1):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale)

    def humanBits(self, value, scale=1):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale, 1000)

    def fmt(self, fmt, value):
        if value is None:
            return UNAVAILABLE
        return fmt % value


def nested_defaultdict(n,typ):
    """create a nested defaultdict n-levels deep, with type typ leaf values"""
    fact = typ
    i = 1
    while i < n:
        fact = lambda f=fact: defaultdict(f)
        i += 1
    return defaultdict(fact)
