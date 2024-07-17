##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import copy
import logging
import logging.config
import sys

import six


def getLogger(obj):
    return logging.getLogger(
        "zen.zenjobs.monitor.{}".format(
            type(obj).__module__.split(".")[-1].lower()
        )
    )


def configure_logging(level=None, filename=None, maxcount=None, maxsize=None):
    config = copy.deepcopy(_logging_config)
    common_handler = config["handlers"]["common"]
    common_handler.update(
        {
            "filename": filename,
            "maxBytes": maxsize,
            "backupCount": maxcount,
        }
    )
    config["loggers"]["zen.zenjobs.monitor"]["level"] = level.upper()
    logging.config.dictConfig(config)


class FormatStringFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument (if omitted, you get the ISO8601 format).
        """
        self._fmt = fmt if fmt else "{message}"
        self.datefmt = datefmt

    def format(self, record):
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string uses the
        time (as determined by a call to usesTime(), formatTime() is
        called to format the event time. If there is exception information,
        it is formatted using formatException() and appended to the message.
        """
        record.message = _getMessage(record)
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        try:
            s = self._fmt.format(**record.__dict__)
        except UnicodeDecodeError as e:
            # Issue 25664. The logger name may be Unicode. Try again ...
            try:
                record.name = record.name.decode("utf-8")
                s = self._fmt.format(**record.__dict__)
            except UnicodeDecodeError:
                raise e
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + record.exc_text
            except UnicodeError:
                # Sometimes filenames have non-ASCII chars, which can lead
                # to errors when s is Unicode and record.exc_text is str
                # See issue 8924.
                # We also use replace for when there are multiple
                # encodings, e.g. UTF-8 for the filesystem and latin-1
                # for a script. See issue 13232.
                s = s + record.exc_text.decode(
                    sys.getfilesystemencoding(), "replace"
                )
        return s

    def usesTime(self):
        """
        Check if the format uses the creation time of the record.
        """
        return self._fmt.find("{asctime}") >= 0


def _getMessage(record):
    """
    Return the message for this LogRecord.

    Return the message for this LogRecord after merging any user-supplied
    arguments with the message.
    """
    msg = record.msg
    if not isinstance(msg, six.string_types):
        try:
            msg = str(record.msg)
        except UnicodeError:
            msg = record.msg  # Defer encoding till later
    if record.args:
        msg = msg.format(*record.args)
    return msg


_logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s.%(msecs).0f %(levelname)s %(name)s: %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "fancy": {
            "()": "Products.Jobber.monitor.logger.FormatStringFormatter",
            "format": (
                "{asctime}.{msecs:03.0f} {levelname} {name} [{funcName}] "
                "{message}"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "common": {
            "formatter": "default",
            "class": "cloghandler.ConcurrentRotatingFileHandler",
            "filename": None,
            "maxBytes": None,
            "backupCount": None,
            "mode": "a",
            "filters": [],
        },
        "default": {
            "class": "logging.handlers.MemoryHandler",
            "capacity": 1,
            "formatter": "default",
            "target": "common",
        },
        "monitor": {
            "class": "logging.handlers.MemoryHandler",
            "capacity": 1,
            "formatter": "fancy",
            "target": "common",
        },
    },
    "loggers": {
        "zen": {
            "level": "INFO",
            "handlers": ["default"],
        },
        "zen.zenjobs.monitor": {
            "level": "INFO",
            "handlers": ["monitor"],
            "propagate": False,
        },
    },
}
