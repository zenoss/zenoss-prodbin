##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from exceptions import ImportError, Exception
from zope.dottedname.resolve import resolve


class ZentinelException(Exception):
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException):
    """When walking a path something along the way wasn't found."""
    pass


class ZenResolveExceptionError(ZentinelException):
    '''failed to resolve exception from twisted.python.failure.Failure
    '''
    pass


def resolveException(failure):
    """
    Resolves a twisted.python.failure into the remote exception type that was
    initially raised.
    """

    # return the original exception
    if isinstance(failure.value, Exception):
        return failure.value

    # try to rebuild the exception from its type string
    if isinstance(failure.type, str):
        return _resolve_exception_by_type(failure)

    # last ditch attempt: raise the original exception and return its value
    try:
        failure.raiseException()
    except Exception as err:
        return err


def _resolve_exception_by_type(failure):
    if failure.type in special_resolvers:
        return special_resolvers[failure.type](failure)

    try:
        exctype = resolve(failure.type)
        return exctype(failure.value, failure.tb)
    except ImportError:
        return ZenResolveExceptionError(
            failure.value,
            failure.tb,
            failure.__dict__
        )


# special resolvers for Exceptions that require additional args
def _resolve_twisted_spread_pb_RemoteError(failure):
    '''special resolution steps for twisted RemoteErrors
    '''
    err_type = resolve(failure.type)
    return err_type(
        remoteType=failure.remoteType(),
        value=failure.getErrorMessage(),
        remoteTraceback=failure.getTracebackObject()
    )


special_resolvers = {
    'twisted.spread.pb.RemoteError': _resolve_twisted_spread_pb_RemoteError,
}
