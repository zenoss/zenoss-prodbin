##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import attr

from attr.validators import instance_of, optional

from Products.ZenCollector.services.config import DeviceProxy


@attr.s(frozen=True, slots=True)
class CacheQuery(object):
    service = attr.ib(validator=instance_of(str), default="*")
    monitor = attr.ib(validator=instance_of(str), default="*")
    device = attr.ib(validator=instance_of(str), default="*")


@attr.s(frozen=True, slots=True)
class CacheKey(object):
    service = attr.ib(validator=instance_of(str))
    monitor = attr.ib(validator=instance_of(str))
    device = attr.ib(validator=instance_of(str))


@attr.s(slots=True)
class CacheRecord(object):
    key = attr.ib(
        validator=instance_of(CacheKey), on_setattr=attr.setters.NO_OP
    )
    uid = attr.ib(validator=instance_of(str), on_setattr=attr.setters.NO_OP)
    updated = attr.ib(validator=instance_of(float))
    config = attr.ib(validator=instance_of(DeviceProxy))

    @classmethod
    def make(cls, svc, mon, dev, uid, updated, config):
        return cls(CacheKey(svc, mon, dev), uid, updated, config)

    @property
    def service(self):
        return self.key.service

    @property
    def monitor(self):
        return self.key.monitor

    @property
    def device(self):
        return self.key.device


@attr.s(slots=True)
class _Status(object):
    """Base class for status classes."""

    key = attr.ib(validator=instance_of(CacheKey))
    uid = attr.ib(validator=optional(instance_of(str)))

    @property
    def has_config(self):
        return self.uid is not None


class _ConfigStatus(object):
    """
    Namespace class for Current, Retired, Expired, Pending, and Building types.
    """

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Current(_Status):
        """The configuration is current."""

        updated = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Retired(_Status):
        """The cofiguration is retired, but not yet expired."""

        retired = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Expired(_Status):
        """The configuration has expired."""

        expired = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Pending(_Status):
        """The configuration is waiting for a rebuild."""

        submitted = attr.ib(validator=instance_of(float))

    @attr.s(slots=True, frozen=True, repr_ns="ConfigStatus")
    class Building(_Status):
        """The configuration is rebuilding."""

        started = attr.ib(validator=instance_of(float))

    def __contains__(self, value):
        return isinstance(
            value,
            (
                _ConfigStatus.Current,
                _ConfigStatus.Retired,
                _ConfigStatus.Expired,
                _ConfigStatus.Pending,
                _ConfigStatus.Building,
            ),
        )


ConfigStatus = _ConfigStatus()

__all__ = (
    "CacheKey",
    "CacheQuery",
    "CacheRecord",
    "ConfigStatus",
)
