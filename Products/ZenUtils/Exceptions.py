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
#   Copyright (c) 2004 Zentinel Systems,Inc. All rights reserved.


class ZentinelException(Exception): 
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException): 
    """When walking a path something along the way wasn't found."""
    pass



