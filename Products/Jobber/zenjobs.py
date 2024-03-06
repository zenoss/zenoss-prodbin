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

from .serialization import without_unicode


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
