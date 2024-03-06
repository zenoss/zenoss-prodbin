##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from celery import Celery
from kombu.serialization import register

import Products.Jobber

from Products.ZenUtils.Utils import load_config

from .serialization import without_unicode


load_config("signals.zcml", Products.Jobber)

# Register custom serializer
register(
    "without-unicode",
    without_unicode.dump,
    without_unicode.load,
    content_type="application/x-without-unicode",
    content_encoding="utf-8",
)

app = Celery(
    "zenjobs",
    config_source="Products.Jobber.config:Celery",
    task_cls="Products.Jobber.task:ZenTask",
)

# Allow considerably more time for the worker_process_init signal
# to complete (rather than the default of 4 seconds).   This is required
# because loading the zenoss environment / zenpacks can take a while.

# celery 3.1.26  (remove once we update celery)
from celery.concurrency import asynpool
asynpool.PROC_ALIVE_TIMEOUT = 300

# celery 4.4.0+
# app.conf.worker_proc_alive_timeout = 300