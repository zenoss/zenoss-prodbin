##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Import celery classes from this package exclusively, as it ensures the
environment has been set up first.
"""
import os

LOADERFQDN = "Products.ZenUtils.celeryintegration.ZenossLoader"

os.environ.setdefault('CELERY_LOADER', LOADERFQDN)

from celery import states

from .loader import ZenossLoader
from .backend import ZODBBackend
from .app import ZenossCelery

from celery.contrib.abortable import AbortableTask as Task, ABORTED

for _attr in ('PROPAGATE_STATES', 'EXCEPTION_STATES', 'READY_STATES', 'ALL_STATES'):
    setattr(states, _attr, frozenset(set((ABORTED,)) | getattr(states, _attr)))
del _attr

from celery.app.state import current_app


def reconfigure_celery(config, updateonly=True):
    """
    Reconfigure Celery with new config.

    @param config: The new configuration to be applied.
    @type config: dict
    @param updateonly: Whether to update the existing config (versus replace)
    @type updateonly: bool
    """
    newconfig = {}
    if updateonly:
        newconfig.update(current_app.conf)
    newconfig.update(config)
    current_app.config_from_object(newconfig)
