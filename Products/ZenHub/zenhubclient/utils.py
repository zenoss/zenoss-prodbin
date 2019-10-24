##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


def getLoggerFrom(logger, obj):
    """Return a logger based on the name of the given class."""
    cls = type(obj)
    return logger.getChild(cls.__name__.lower())
