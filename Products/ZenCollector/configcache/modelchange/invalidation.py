##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from enum import IntEnum

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


class InvalidationCause(IntEnum):
    """An enumeration of reasons for the invalidation."""

    Removed = 1
    Updated = 2


class Invalidation(object):
    """Contains the OID and the device referenced by the OID."""

    __slots__ = ("oid", "device", "reason")

    def __init__(self, oid, device, reason):
        """
        Initialize an Invalidation instance.

        :param oid: The object ID of the invalidated device.
        :type oid: zodbpickle.binary
        :param device: The invalidated device
        :type device: PrimaryPathObjectManager | DeviceComponent
        :param reason: The reason why the device was invalidated.
        :type reason: InvalidationCause
        """
        self.oid = oid
        self.device = device
        self.reason = reason

    def __eq__(self, other):
        if isinstance(other, Invalidation):
            return all(
                getattr(self, attr) == getattr(other, attr)
                for attr in self.__slots__
            )
        return False

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return "<Invalidation: oid=%r device=%s reason=%s>" % (
            self.oid,
            self.device,
            self.reason,
        )
