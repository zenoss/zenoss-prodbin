##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface


class ComponentGridSpec(object):
    """
    A named utility that does a thing.
    """
    def __init__(self):
        self.fields = []