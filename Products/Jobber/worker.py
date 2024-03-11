##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import time
import ZODB.config

from .config import ZenJobs
from .utils.app import get_app

_mlog = logging.getLogger("zen.zenjobs.worker")


def initialize_zenoss_env(**kw):
    start = time.time()

    from OFS.Application import import_products
    from Zope2.App import zcml

    import Products.ZenWidgets

    from Products.ZenUtils.Utils import load_config_override

    import_products()
    zcml.load_site()
    load_config_override("scriptmessaging.zcml", Products.ZenWidgets)

    _mlog.getChild("initialize_zenoss_env").info(
        "Zenoss environment initialized (%.2f sec elapsed)"
        % (time.time() - start)
    )


def report_tasks(**kw):
    """Log the tasks Celery knows about."""
    log = _mlog.getChild("report_tasks")
    log.info("Registered job classes:")
    for taskname in sorted(get_app().tasks.keys()):
        log.info(".. %s", taskname)


def setup_zodb(**kw):
    """Initialize a ZODB connection."""
    zodbcfg = ZenJobs.get("zodb-config-file")
    url = "file://%s" % zodbcfg
    get_app().db = ZODB.config.databaseFromURL(url)
    _mlog.getChild("setup_zodb").info("ZODB connection initialized")


def teardown_zodb(**kw):
    """Shut down the ZODB connection."""
    get_app().db.close()
    _mlog.getChild("teardown_zodb").info("ZODB connection closed")
