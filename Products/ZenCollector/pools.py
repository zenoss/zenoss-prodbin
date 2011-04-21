###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """pool

Pool resources and provide an infrastructure for interacting with them.

"""

class ResourcePool(object):
    """
    Container object for allocating shared resources.
    """

    def __init__(self, name):
        self.name = name
        self.minCount = None
        self.maxCount = None
        self._resources = {}


# Manage all pools
globalAllocater = {}

def getResourcePool(name, factory=ResourcePool):
    return getPool(name, factory)

def getPool(name, factory=None):
    """
    Return the named pool.
    If the factory is None, a simple dictionary is created and returned.

    @parameter name: name of the pool
    @type name: string
    @parameter factory: class to use to construct the resource pool or None
    @type factory: class that takes only one argument as a constructor (the name)
    """
    if name not in globalAllocater:
        if factory is None:
            globalAllocater[name] = {}
        else:
            globalAllocater[name] = factory(name)
    return globalAllocater[name]

