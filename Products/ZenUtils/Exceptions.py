##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


class ZentinelException(Exception): 
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException): 
    """When walking a path something along the way wasn't found."""
    pass
