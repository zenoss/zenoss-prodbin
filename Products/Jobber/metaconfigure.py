##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from celery import signals


def job(_context, class_, name=None):
    """Nothing to do.

    When the task is loaded, it's registered with Celery.
    """
    pass


def signal(_context, name, handler):
    """Register a Celery signal handler."""
    signal = getattr(signals, name, None)
    if signal is None:
        raise AttributeError("Unknown signal name '%s'" % name)
    handler_fn = _context.resolve(handler)
    signal.connect(handler_fn)
