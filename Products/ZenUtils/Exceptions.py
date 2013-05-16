##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
import sys
from exceptions import ImportError, Exception
from zope.dottedname.resolve import resolve


class ZentinelException(Exception): 
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException): 
    """When walking a path something along the way wasn't found."""
    pass


def resolveException(failure):
    """
    Resolves a twisted.python.failure into the remote exception type that was
    initially raised.
    """

    #raise the original exception
    excvalue = failure.value
    if isinstance(excvalue, Exception):
        return excvalue

    #if the original exception is a string, assume it defines a python exception
    exctype = failure.type
    if isinstance(exctype, basestring):
        try:
            exctype = resolve(failure.type)
        except ImportError:
            exctype = Exception
        return exctype(excvalue, failure.tb)

    #raise the original exception and return its value
    try:
        failure.raiseException()
    except:
        return sys.exc_info()[1]
