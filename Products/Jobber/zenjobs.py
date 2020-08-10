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

app = Celery(
    "zenjobs",
    config_source="Products.Jobber.config:Celery",
    task_cls="Products.Jobber.task:ZenTask",
)
