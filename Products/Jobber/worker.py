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
import time
import ZODB.config

from .config import ZenJobs

mlog = logging.getLogger("zen.zenjobs.worker")


def initialize_zenoss_env(**kw):
    start = time.time()
    from Zope2.App import zcml
    import Products.Jobber
    import Products.ZenWidgets
    from OFS.Application import import_products
    from Products.ZenUtils.Utils import load_config, load_config_override
    from Products.ZenUtils.zenpackload import load_zenpacks

    import_products()
    # load_zenpacks()  # already called by import_products via Products.ZenossStartup
    zcml.load_site()
    load_config("signals.zcml", Products.Jobber)
    load_config_override('scriptmessaging.zcml', Products.ZenWidgets)
    mlog.getChild("initialize_zenoss_env").info("Zenoss environment initialized (%d sec elapsed)" % (time.time() - start))


def setup_zodb(**kw):
    """Initialize a ZODB connection."""
    from .zenjobs import app

    zodbcfg = ZenJobs.get("zodb-config-file")
    url = "file://%s" % zodbcfg
    app.db = ZODB.config.databaseFromURL(url)
    mlog.getChild("setup_zodb").info("ZODB connection initialized")


def teardown_zodb(**kw):
    """Shut down the ZODB connection."""
    from .zenjobs import app

    app.db.close()
    mlog.getChild("teardown_zodb").info("ZODB connection closed")
