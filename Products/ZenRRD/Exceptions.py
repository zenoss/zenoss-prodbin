#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################


from Products.ZenUtils.Exceptions import ZentinelException


class RRDException(ZentinelException): pass

class RRDObjectNotFound(RRDException): pass

class TooManyArgs(RRDException): pass

class RRDTemplateError(RRDException): pass

class RRDGraphError(RRDException): pass

