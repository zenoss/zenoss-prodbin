##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import ZODB.config

from .config import ZenJobs
from .zenjobs import app

mlog = logging.getLogger("zen.zenjobs.worker")


def setup_zodb(**kw):
    """Initialize a ZODB connection."""
    zodbcfg = ZenJobs.get("zodb-config-file")
    url = "file://%s" % zodbcfg
    app.db = ZODB.config.databaseFromURL(url)
    mlog.getChild("setup_zodb").info("ZODB connection initialized")


def teardown_zodb(**kw):
    """Shut down the ZODB connection."""
    app.db.close()
    mlog.getChild("teardown_zodb").info("ZODB connection closed")
