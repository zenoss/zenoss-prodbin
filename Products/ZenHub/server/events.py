##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.interface import implementer

from ..interfaces import IServiceAddedEvent


@implementer(IServiceAddedEvent)
class ServiceAddedEvent(object):
    """An event class dispatched when a service is first loaded."""

    def __init__(self, name, instance):
        """Initialize a ServiceAddedEvent instance.

        @param name {str} Name of the service.
        @param instance {str} Name of the performance monitor (collector).
        """
        self.name = name
        self.instance = instance
