##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import importlib
import itertools
import logging
import time

import pathlib2 as pathlib
import Products
import ZODB.config

from Zope2.App import zcml

from .config import getConfig
from .utils.app import get_app

_mlog = logging.getLogger("zen.zenjobs.worker")


def initialize_zenoss_env(**kw):
    start = time.time()

    from OFS.Application import import_products
    from Zope2.App import zcml

    import Products.ZenWidgets

    from Products.ZenUtils.Utils import load_config_override
    from Products.ZenUtils.zenpackload import load_zenpacks

    import_products()

    # The Zenoss environment requires that the 'zenoss.zenpacks' entrypoints
    # be explicitely loaded because celery doesn't know to do that.
    # Not loading those entrypoints means that celery will be unaware of
    # any celery 'task' definitions in the ZenPacks.
    load_zenpacks()

    zcml.load_site()
    load_config_override("scriptmessaging.zcml", Products.ZenWidgets)

    _mlog.getChild("initialize_zenoss_env").info(
        "Zenoss environment initialized (%.2f sec elapsed)"
        % (time.time() - start)
    )


def register_tasks(**kw):
    # defer import ZenPacks until here because it doesn't exist during
    # an image build.
    import ZenPacks

    search_paths = tuple(
        pathlib.Path(p)
        for p in itertools.chain(Products.__path__, ZenPacks.__path__)
    )
    zcml_files = (
        fn for path in search_paths for fn in path.rglob("**/jobs.zcml")
    )
    for fn in zcml_files:
        root = next(
            (
                p
                for p in search_paths
                if fn.as_posix().startswith(p.as_posix())
            ),
            None,
        )
        if root is None:
            continue
        modroot = len(root.parts) - 1
        modname = ".".join(fn.parent.parts[modroot:])
        module = importlib.import_module(modname)
        zcml.load_config(fn.name, module)


def report_tasks(**kw):
    """Log the tasks Celery knows about."""
    log = _mlog.getChild("report_tasks")
    log.info("Registered job classes:")
    for taskname in sorted(get_app().tasks.keys()):
        log.info(".. %s", taskname)


def setup_zodb(**kw):
    """Initialize a ZODB connection."""
    zodbcfg = getConfig().get("zodb-config-file")
    url = "file://%s" % zodbcfg
    get_app().db = ZODB.config.databaseFromURL(url)
    _mlog.getChild("setup_zodb").info("ZODB connection initialized")


def teardown_zodb(**kw):
    """Shut down the ZODB connection."""
    get_app().db.close()
    _mlog.getChild("teardown_zodb").info("ZODB connection closed")
