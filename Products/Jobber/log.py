##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import contextlib
import csv
import hashlib
import logging
import logging.config
import logging.handlers
import os
import sys
import threading

from inotify_simple import INotify, flags as Flags
from zope.component import getUtility

from Products.ZenUtils.Utils import zenPath

from .config import ZenJobs
from .exceptions import NoSuchJobException
from .interfaces import IJobStore
from .utils.algorithms import partition
from .utils.log import (
    FormatStringAdapter,
    get_logger,
    get_task_logger,
    ForwardingHandler,
    inject_logger,
    LoggingProxy,
    TaskLogFileHandler,
)

_default_log_level = logging.getLevelName(ZenJobs.get("logseverity"))

_default_config = {
    "worker": {
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
                "filename":
                    os.path.join(ZenJobs.get("logpath"), "zenjobs.log"),
                "maxBytes": ZenJobs.get("maxlogsize") * 1024,
                "backupCount": ZenJobs.get("maxbackuplogs"),
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
                "propagate": False,
            },
            "celery": {
                "level": _default_log_level,
            },
        },
        "root": {
            "handlers": ["main"],
        },
    },
    "beat": {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "beat": {
                "format": (
                    "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: "
                    "%(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "beat": {
                "formatter": "beat",
                "class": "cloghandler.ConcurrentRotatingFileHandler",
                "filename": os.path.join(
                    ZenJobs.get("logpath"), "zenjobs-scheduler.log",
                ),
                "maxBytes": ZenJobs.get("maxlogsize") * 1024,
                "backupCount": ZenJobs.get("maxbackuplogs"),
                "mode": "a",
            },
        },
        "loggers": {
            "STDOUT": {
                "level": _default_log_level,
            },
            "zen": {
                "level": _default_log_level,
            },
            "celery": {
                "level": _default_log_level,
            },
        },
        "root": {
            "handlers": ["beat"],
        },
    },
}

_loglevelconf_filepath = zenPath("etc", "zenjobs_log_levels.conf")


def _get_logger(name=None):
    if name:
        name = ".".join(("zen", "zenjobs", "log", name))
    else:
        name = "zen.zenjobs.log"
    return get_logger(name)


def get_default_config(name):
    """Return the default logging configuration for the given name.

    :rtype: dict
    """
    return _default_config[name]


def configure_logging(logfile=None, **kw):
    """Configure logging for zenjobs."""
    # Sketchy hack.  Determine the logging config based on whether
    # the logfile parameter is not None.
    config_name = "worker" if logfile is None else "beat"
    logging.config.dictConfig(get_default_config(config_name))

    if os.path.exists(_loglevelconf_filepath):
        levelconfig = load_log_level_config(_loglevelconf_filepath)
        apply_levels(levelconfig)

    stdout_logger = logging.getLogger("STDOUT")
    outproxy = LoggingProxy(stdout_logger)
    sys.__stdout__ = outproxy
    sys.stdout = outproxy

    stderr_logger = logging.getLogger("STDERR")
    errproxy = LoggingProxy(stderr_logger)
    sys.__stderr__ = errproxy
    sys.stderr = errproxy

    if config_name == "beat":
        # The celery.beat module has a novel approach to getting its
        # logger, so fixing things so log messages can get sent where
        # we see them.
        from celery import beat
        from logging import getLogger
        log = getLogger("celery.beat")
        beat.info = log.info
        beat.debug = log.debug
        beat.error = log.error
        beat.warning = log.warning

    log = FormatStringAdapter(_get_logger())
    log.info("configure_logging: Logging configured")


def load_log_level_config(configfile):
    """Return the log level configuration data.

    The data maps the log name to the log level name.

    :rtype: dict
    """
    with open(configfile, 'r') as fd:
        reader = csv.reader(
            fd, delimiter=' ',
            quoting=csv.QUOTE_NONE, skipinitialspace=True,
        )
        return dict(row[:2] for row in reader)


def apply_levels(loggerlevels):
    """Apply the log levels specified in loggerlevels."""
    # If no data is given, then do nothing.
    if not loggerlevels:
        return

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
    _get_logger().debug(
        "Updated log level of logger(s) %s", ", ".join(loggerlevels),
    )

    # Set the level of all loggers not given in the loglevel config file
    # to NOTSET.
    rlog = logging.getLogger()
    loggers = {
        name: logger
        for name, logger in rlog.manager.loggerDict.iteritems()
        if not isinstance(logger, logging.PlaceHolder)
        and logger.level > logging.NOTSET
        and name not in loggerlevels
    }
    for logger in loggers.values():
        logger.setLevel(logging.NOTSET)
    if loggers:
        _get_logger().debug(
            "Reset log level of loggers %s", ", ".join(loggers),
        )


@inject_logger(log=_get_logger, adapter=FormatStringAdapter)
def setup_job_instance_logger(log, task_id=None, task=None, **kwargs):
    """Create and configure the job instance logger."""
    if task.ignore_result:
        # Switch propagation on so that log messages are written to the
        # main zenjobs log.
        get_task_logger().propagate = True
        log.debug("Task ignores result; skipping job instance log setup")
        return

    log.debug("Adding a logger for job instance {}[{}]", task.name, task_id)
    try:
        storage = getUtility(IJobStore, "redis")
        if task_id not in storage:
            raise NoSuchJobException(task_id)

        logfile = storage.getfield(task_id, "logfile")
        logdir = os.path.dirname(logfile)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        handler = TaskLogFileHandler(logfile)
        get_task_logger().addHandler(handler)

        # Redirect zen logging to task log handler
        zenlog = logging.getLogger("zen")
        zenlog.propagate = False
        zenlog.addHandler(handler)

        # Add a handler to the STDOUT and STDERR loggers
        newhandler = ForwardingHandler(handler)
        # newhandler.setFormatter(logging.Formatter("%(message)s"))
        loggers = (logging.getLogger("STDOUT"), logging.getLogger("STDERR"))
        for logger in loggers:
            logger.propagate = False
            logger.addHandler(newhandler)
    except Exception:
        log.exception("Failed to add job instance logger")
    else:
        log.debug("Job instance logger added")


@inject_logger(log=_get_logger, adapter=FormatStringAdapter)
def teardown_job_instance_logger(log, task=None, **kwargs):
    """Tear down and delete the job instance logger."""
    if task.ignore_result:
        get_task_logger().propagate = False
        return
    log.debug("Removing job instance logger from {}", task.name)
    try:
        # Remove handler from STDOUT and STDERR loggers
        loggers = (logging.getLogger("STDOUT"), logging.getLogger("STDERR"))
        oldhandlers = set()
        for logger in loggers:
            logger.propagate = True
            removedhandlers, handlers = partition(
                logger.handlers,
                lambda x: isinstance(x, ForwardingHandler)
            )
            logger.handlers = handlers
            oldhandlers.update(removedhandlers)
        for h in oldhandlers:
            h.close()

        # Restore zen logging
        zenlog = logging.getLogger("zen")
        zenlog.propagate = True
        zenlog.handlers = []

        # Close task logger
        tasklog = get_task_logger()
        taskhandlers, handlers = partition(
            tasklog.handlers,
            lambda x: isinstance(x, TaskLogFileHandler)
        )
        tasklog.handlers = handlers
        for h in taskhandlers:
            h.close()
    except Exception:
        log.exception("Failed to remove job instance logger")
    else:
        log.debug("Job instance logger removed")


@inject_logger(log=_get_logger, adapter=FormatStringAdapter)
def setup_loglevel_monitor(log, *args, **kwargs):
    LogLevelUpdater.start()
    log.debug("Started log levels config monitoring thread")


@inject_logger(log=_get_logger, adapter=FormatStringAdapter)
def teardown_loglevel_monitor(log, *args, **kwargs):
    LogLevelUpdater.stop()
    log.debug("Stopped log levels config monitoring thread")


class LogLevelUpdater(object):
    """Manages the log levels updater."""

    instance = None

    @classmethod
    def start(cls):
        if cls.instance is None:
            cls.instance = _LogLevelUpdaterThread(_loglevelconf_filepath)
            cls.instance.start()
        elif not cls.instance.is_alive():
            cls.instance = None
            cls.start()

    @classmethod
    def stop(cls):
        if cls.instance is not None:
            cls.instance.stop()


class _LogLevelUpdaterThread(threading.Thread):

    def __init__(self, filepath):
        self.__filepath = filepath
        self.__hashed = _get_hash(load_log_level_config(self.__filepath))
        self.__stop = threading.Event()
        super(_LogLevelUpdaterThread, self).__init__()
        self.daemon = True

    def _log(self):
        return _get_logger("loglevelupdater")

    def stop(self):
        self.__stop.set()

    def run(self):
        try:
            with file_watcher(self.__filepath) as watcher:
                while not self.__stop.wait(0.1):
                    if not watcher.changed:
                        continue
                    log = self._log()
                    try:
                        config = load_log_level_config(self.__filepath)
                        # Verify the file has actually changed.
                        hashed = _get_hash(config)
                        if hashed == self.__hashed:
                            continue
                        # The configuration has changed.
                        self.__hashed = hashed
                        log.info("log levels config has changed")
                        apply_levels(config)
                    except Exception as ex:
                        log.error("config file bad format: %s", ex)
                    else:
                        log.info("log levels config changes applied")
        finally:
            self._log().info("stopping")


def _get_hash(config):
    return hashlib.md5(
        ''.join("{0}{1}".format(k, config[k]) for k in sorted(config))
    ).hexdigest()


@contextlib.contextmanager
def file_watcher(filepath):
    watcher = FileChangeWatcher(filepath)
    try:
        yield watcher
    finally:
        watcher.close()


class FileChangeWatcher(object):
    """Monitors for changes in a given file."""

    def __init__(self, filepath):
        self.__path, self.__name = filepath.rsplit("/", 1)
        self.__inotify = INotify()
        watch_flags = \
            Flags.MODIFY \
            | Flags.CLOSE_WRITE \
            | Flags.MOVED_TO \
            | Flags.EXCL_UNLINK
        self.__wd = self.__inotify.add_watch(self.__path, watch_flags)

    def close(self):
        self.__inotify.rm_watch(self.__wd)

    @property
    def changed(self):
        modified = saved = False
        events = self.__inotify.read()
        events = (e for e in events if e.name == self.__name)
        flags = (f for e in events for f in Flags.from_mask(e.mask))
        for flag in flags:
            if flag == Flags.MODIFY:
                modified = True
            elif flag == Flags.CLOSE_WRITE:
                saved = True
            elif flag == Flags.MOVED_TO:
                modified = saved = True
        return modified and saved
