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

from attr.validators import instance_of

from Products.ZenCollector.services.config import DeviceProxy


@attr.s(frozen=True, slots=True)
class ConfigQuery(object):
    service = attr.ib(validator=[instance_of(str)], default="*")
    monitor = attr.ib(validator=[instance_of(str)], default="*")
    device = attr.ib(validator=[instance_of(str)], default="*")


@attr.s(frozen=True, slots=True)
class ConfigKey(object):
    service = attr.ib(validator=[instance_of(str)])
    monitor = attr.ib(validator=[instance_of(str)])
    device = attr.ib(validator=[instance_of(str)])


@attr.s(frozen=True, slots=True)
class ConfigId(object):
    key = attr.ib(validator=[instance_of(ConfigKey)])
    uid = attr.ib(validator=[instance_of(str)])


@attr.s(slots=True)
class ConfigRecord(object):
    key = attr.ib(
        validator=[instance_of(ConfigKey)], on_setattr=attr.setters.NO_OP
    )
    uid = attr.ib(validator=[instance_of(str)], on_setattr=attr.setters.NO_OP)
    updated = attr.ib(validator=[instance_of(float)])
    config = attr.ib(validator=[instance_of(DeviceProxy)])

    @classmethod
    def make(cls, svc, mon, dev, uid, updated, config):
        return cls(ConfigKey(svc, mon, dev), uid, updated, config)

    @property
    def service(self):
        return self.key.service

    @property
    def monitor(self):
        return self.key.monitor

    @property
    def device(self):
        return self.key.device


class _ConfigStatus(object):
    """
    Namespace class for Current, Building, Expired, and Pending types.
    """

    class Current(object):
        """The configuration is current."""

        def __init__(self, ts):
            self.updated = ts

        def __eq__(self, other):
            if not isinstance(other, _ConfigStatus.Current):
                return NotImplemented
            return self.updated == other.updated

    class Retired(object):
        """The cofiguration is retired, but not yet expired."""

        def __init__(self, ts):
            self.updated = ts

        def __eq__(self, other):
            if not isinstance(other, _ConfigStatus.Retired):
                return NotImplemented
            return self.updated == other.updated

    class Expired(object):
        """The configuration has expired."""

        def __init__(self, ts):
            self.expired = ts

        def __eq__(self, other):
            if not isinstance(other, _ConfigStatus.Expired):
                return NotImplemented
            return True

    class Pending(object):
        """The configuration is waiting for a rebuild."""

        def __init__(self, ts):
            self.submitted = ts

        def __eq__(self, other):
            if not isinstance(other, _ConfigStatus.Pending):
                return NotImplemented
            return self.submitted == other.submitted

    class Building(object):
        """The configuration is rebuilding."""

        def __init__(self, ts):
            self.started = ts

        def __eq__(self, other):
            if not isinstance(other, _ConfigStatus.Building):
                return NotImplemented
            return self.started == other.started

    def __contains__(self, value):
        return isinstance(
            value,
            (
                _ConfigStatus.Building,
                _ConfigStatus.Current,
                _ConfigStatus.Expired,
                _ConfigStatus.Pending,
            ),
        )


ConfigStatus = _ConfigStatus()

__all__ = (
    "ConfigKey",
    "ConfigQuery",
    "ConfigRecord",
    "ConfigStatus",
)
