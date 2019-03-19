##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import csv
import errno
import logging
import logging.config
import logging.handlers
import os
import sys

from Products.ZenUtils.Utils import zenPath

from .config import ZenJobs
from .utils.log import (
    FormatStringAdapter,
    get_logger,
    get_task_logger,
    inject_logger,
    LoggingProxy,
    TaskLogFileHandler,
)

_default_log_level = logging.getLevelName(ZenJobs.getint("logseverity"))

_default_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "main": {
            "()": "Products.Jobber.utils.log.WorkerFilter",
        },
    },
    "formatters": {
        "main": {
            "()": "Products.Jobber.utils.log.TaskFormatter",
            "base": (
                "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: "
                "worker=%(instance)s/%(processName)s: %(message)s"
            ),
            "task": (
                "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: "
                "worker=%(instance)s/%(processName)s "
                "task=%(taskname)s taskid=%(taskid)s: %(message)s "
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "main": {
            "formatter": "main",
            "class": "cloghandler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(ZenJobs.get("logpath"), "zenjobs.log"),
            "maxBytes": ZenJobs.getint("maxlogsize") * 1024,
            "backupCount": ZenJobs.getint("maxbackuplogs"),
            "mode": "a",
            "filters": ["main"],
        },
    },
    "loggers": {
        "STDOUT": {
            "level": _default_log_level,
        },
        "zen": {
            "level": _default_log_level,
        },
        "zen.zenjobs": {
            "level": _default_log_level,
            "propagate": False,
            "handlers": ["main"],
        },
        "zen.zenjobs.job": {
            "level": _default_log_level,
        },
        "celery": {
            "level": _default_log_level,
        },
    },
    "root": {
        "handlers": ["main"],
    },
}


def _get_default_config():
    return _default_config


def configure_logging(**ignore):
    """Configure logging for zenjobs."""
    logging.config.dictConfig(_get_default_config())

    loglevel_configfile = zenPath("etc", "zenjobs_log_levels.conf")
    if os.path.exists(loglevel_configfile):
        with open(loglevel_configfile, 'r') as fd:
            reader = csv.reader(
                fd, delimiter=' ',
                quoting=csv.QUOTE_NONE, skipinitialspace=True,
            )
            levelconfig = dict(row for row in reader)
        _apply_levels(levelconfig)

    stdout = logging.getLogger("STDOUT")
    outproxy = LoggingProxy(stdout, logging.INFO)
    sys.__stdout__ = outproxy
    sys.stdout = outproxy

    stderr = logging.getLogger("STDERR")
    errproxy = LoggingProxy(stderr, logging.ERROR)
    sys.__stderr__ = errproxy
    sys.stderr = errproxy

    log = FormatStringAdapter(get_logger())
    log.debug("configure_logging: Logging configured")


def _apply_levels(loggerlevels):
    """Apply the log levels specified in loggerlevels."""
    # 'Special' logger names are recognized and are retrieved using
    # logging.getLogger rather than get_logger.  These special logger names
    # are STDOUT, STDERR, and any log names starting with 'zen' or 'celery'.
    for name, level in loggerlevels.iteritems():
        if (
            any(name.startswith(pre) for pre in ("zen", "celery"))
            or name in ("STDOUT", "STDERR")
        ):
            logger = logging.getLogger(name)
        else:
            logger = get_logger(name)
        logger.setLevel(level)


@inject_logger(log=get_logger, adapter=FormatStringAdapter)
def setup_job_instance_logger(log, task_id=None, task=None, **kwargs):
    """Create and configure the job instance logger."""
    log.debug("Adding a logger for job instance {}[{}]", task.name, task_id)
    try:
        logdir = ZenJobs.get("job-log-path")
        try:
            os.makedirs(logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        logfile = os.path.join(logdir, "%s.log" % task_id)
        handler = TaskLogFileHandler(logfile)
        for logger in (logging.getLogger("zen"), get_task_logger()):
            logger.addHandler(handler)
    except Exception:
        log.exception("Failed to add job instance logger")
    finally:
        log.debug("Job instance logger added")


@inject_logger(log=get_logger, adapter=FormatStringAdapter)
def teardown_job_instance_logger(log, task=None, **kwargs):
    """Tear down and delete the job instance logger."""
    log.debug("Removing job instance logger from {}", task.name)
    try:
        for logger in (logging.getLogger("zen"), get_task_logger()):
            handlers = []
            for handler in logger.handlers:
                if isinstance(handler, TaskLogFileHandler):
                    handler.close()
                else:
                    handlers.append(handler)
            logger.handlers = handlers
    except Exception:
        log.exception("Failed to remove job instance logger")
    finally:
        log.debug("Job instance logger removed")
