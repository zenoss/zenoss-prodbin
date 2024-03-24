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
from celery.bin import Option
from kombu.serialization import register

from .serialization import without_unicode

# Register custom serializer
register(
    "without-unicode",
    without_unicode.dump,
    without_unicode.load,
    content_type="application/x-without-unicode",
    content_encoding="utf-8",
)

app = Celery("zenjobs", task_cls="Products.Jobber.task:ZenTask")
app.user_options["preload"].add(
    Option(
        "--config-file", default=None, help="Name of the configuration file"
    )
)

# Allow considerably more time for the worker_process_init signal
# to complete (rather than the default of 4 seconds).   This is required
# because loading the zenoss environment / zenpacks can take a while.

# celery 3.1.26  (remove once we update celery)
from celery.concurrency import asynpool  # noqa E402

asynpool.PROC_ALIVE_TIMEOUT = 300

# celery 4.4.0+
# Set Products.Jobber.config.Celery.worker_proc_alive_timeout = 300
