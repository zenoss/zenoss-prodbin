##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from ...events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)


def received(task):
    """Return a ServiceCallReceived object."""
    data = dict(task.event_data)
    data["timestamp"] = task.received_tm
    return ServiceCallReceived(**data)


def started(task):
    """Return a ServiceCallStarted object."""
    data = dict(task.event_data)
    data.update({"timestamp": task.started_tm, "attempts": task.attempt})
    return ServiceCallStarted(**data)


def completed(task, key, value):
    """Return a ServiceCallCompleted object."""
    data = dict(task.event_data)
    data.update(
        {
            "timestamp": task.completed_tm,
            "attempts": task.attempt,
            key: value,
        }
    )
    return ServiceCallCompleted(**data)
