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
import errno
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
from .interfaces import IJobStore
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


_loglevelconf_filepath = zenPath("etc", "zenjobs_log_levels.conf")


def _get_logger(name=None):
    if name:
        name = ".".join(("zen", "zenjobs", "log", name))
    else:
        name = "zen.zenjobs.log"
    return get_logger(name)


def get_default_config():
    """Return the default logging configuration.

    :rtype: dict
    """
    return _default_config


def configure_logging(**ignore):
    """Configure logging for zenjobs."""
    logging.config.dictConfig(get_default_config())

    if os.path.exists(_loglevelconf_filepath):
        levelconfig = load_log_level_config(_loglevelconf_filepath)
        apply_levels(levelconfig)

    stdout = logging.getLogger("STDOUT")
    outproxy = LoggingProxy(stdout, logging.INFO)
    sys.__stdout__ = outproxy
    sys.stdout = outproxy

    stderr = logging.getLogger("STDERR")
    errproxy = LoggingProxy(stderr, logging.ERROR)
    sys.__stderr__ = errproxy
    sys.stderr = errproxy

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
    log.debug("Adding a logger for job instance {}[{}]", task.name, task_id)
    try:
        storage = getUtility(IJobStore, "redis")
        logfile = storage.getfield(task_id, "logfile")
        logdir = os.path.dirname(logfile)
        try:
            os.makedirs(logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        handler = TaskLogFileHandler(logfile)
        for logger in (logging.getLogger("zen"), get_task_logger()):
            logger.addHandler(handler)
    except Exception:
        log.exception("Failed to add job instance logger")
    finally:
        log.debug("Job instance logger added")


@inject_logger(log=_get_logger, adapter=FormatStringAdapter)
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
