##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Import celery classes from this package exclusively, as it ensures the
environment has been set up first.
"""

# NOTE: the order of statements in this module is important.

LOADER_FQCN = "Products.ZenUtils.celeryintegration.ZenossLoader"

import os
# Set the 'loader' class the default celery app will use.  This setting
# must be made at this point before any other celery-related import.
os.environ.setdefault("CELERY_LOADER", LOADER_FQCN)

from celery import current_app, states, chain
from celery.utils.log import get_task_logger

from .loader import ZenossLoader
from .backend import ZODBBackend

# The Task must be imported AFTER ZenossLoader and ZODBBackend are imported,
# otherwise these names will not be available when Task is imported.
# Celery tasks are configured and registered when imported so AbortableTask
# must be delayed until backend configuration is ready.
from celery.contrib.abortable import AbortableTask as Task


def _patchstate():
    from celery.contrib.abortable import ABORTED
    groupings = (
            'PROPAGATE_STATES', 'EXCEPTION_STATES',
            'READY_STATES', 'ALL_STATES'
        )
    for attr in groupings:
        setattr(
            states, attr,
            frozenset(set((ABORTED,)) | getattr(states, attr))
        )
    setattr(states, 'ABORTED', ABORTED)
_patchstate()
del _patchstate
