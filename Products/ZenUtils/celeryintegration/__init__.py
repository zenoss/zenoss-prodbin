###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """
Import celery classes from this package exclusively, as it ensures the
environment has been set up first.
"""
import os

LOADERFQDN = "Products.ZenUtils.celeryintegration.ZenossLoader"

os.environ.setdefault('CELERY_LOADER', LOADERFQDN)


from .loader import ZenossLoader
from .backend import ZODBBackend
from .app import ZenossCelery


# Set the default app to be ours
import celery.app
celery.app.default_app = ZenossCelery(loader=LOADERFQDN,
                                      set_as_current=False,
                                      accept_magic_kwargs=True)

from celery.task import Task
