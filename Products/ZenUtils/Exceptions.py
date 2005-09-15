#################################################################
#
#   Copyright (c) 2004 Zentinel Systems,Inc. All rights reserved.
#
#################################################################


class ZentinelException(Exception): 
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException): 
    """When walking a path something along the way wasn't found."""
    pass
