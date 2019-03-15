##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from celery.registry import tasks


def job(_context, class_, name=None):
    """Register the given class as a Celery task."""
    if name is not None:
        class_.name = name
    tasks.register(class_)
