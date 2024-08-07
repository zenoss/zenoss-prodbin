##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import atexit
import errno
# import fcntl
import logging
import os
import tempfile

import pathlib2 as pathlib

from Products.ZenUtils.Utils import zenPath

log = logging.getLogger("zen.pid")


def add_pidfile_arguments(parser, basename=None):
    if basename is None:
        basename = parser.prog
    dirname = os.path.join(zenPath("var"), "run")
    parser.add_argument(
        "--pidfile",
        default=os.path.join(dirname, "{}.pid".format(basename)),
        type=_add_pid_suffix,
        help="Pathname of the PID file.  If a directory path is not "
        "specified, the pidfile is saved to {}/.  Note that the actual "
        "filename will contain additional random characters".format(dirname),
    )


def _add_pid_suffix(v):
    if not v.endswith(".pid"):
        if not os.path.basename(v):
            raise ValueError("no filename for pid file given")
        return v + ".pid"
    return v


class PIDFile(object):
    """
    Write a file containing the current process's PID.

    The context manager yields the PID value to the caller.
    """

    def __init__(self, pathname):
        pidfilename = pathlib.Path(pathname)
        dirname = pidfilename.parent
        if dirname.as_posix() == ".":
            dirname = pathlib.Path(zenPath()) / "var" / "run"
        if not dirname.exists():
            raise RuntimeError("not a directory  directory={}".format(dirname))
        self._dirname = dirname.as_posix()
        self._basename = pidfilename.stem
        self._pathname = None

    @property
    def pathname(self):
        return self._pathname

    def __enter__(self):
        self.create(delete=False)
        return self

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        self.remove()

    def read(self):
        """
        Returns the PID stored in the pidfile.

        If the pidfile has not been created, an IOError is raised.

        @rtype: int
        """
        if not self._pathname:
            raise IOError("no pidfile")
        with open(self._pathname, "r") as fp:
            return _read_pidfile(fp)

    def create(self, delete=True):
        """
        Create the pidfile.

        This method does nothing if the pidfile has already been created.

        @param delete: If True, delete the pidfile when the program exits.
        @type delete: bool
        """
        if self._pathname:
            return

        if delete:
            atexit.register(self.remove)

        fp, self._pathname = tempfile.mkstemp(
            dir=self._dirname,
            prefix="{}-".format(self._basename),
            suffix=".pid",
            text=True,
        )
        os.write(fp, str(os.getpid()))
        os.close(fp)

        # self.fp = open(self.pathname, "a+")
        # try:
        #     _flock(self.fp.fileno())
        # except IOError as ex:
        #     raise RuntimeError(
        #         "pidfile already locked  pidfile={} error={}".format(
        #             self.pathname, ex
        #         )
        #     )
        # oldpid = _read_pidfile(self.fp)
        # if oldpid is not None and pid_exists(oldpid):
        #     raise RuntimeError("PID is still running  pid={}".format(oldpid))
        # self.fp.seek(0)
        # self.fp.truncate()
        # self.fp.write("{}\n".format(pid))
        # self.fp.flush()
        # self.fp.seek(0)

    def remove(self):
        if not self._pathname:
            return
        try:
            os.unlink(self._pathname)
            self._pathname = None
        except IOError as ex:
            if ex.errno != errno.EBADF:
                raise
        # if not self.fp:
        #     return
        # try:
        #     self.fp.close()  # deletes the temporary file
        #     self.fp = None  # so subsequent calls to `close` exit early
        #     self.pathname = None
        # except IOError as ex:
        #     if ex.errno != errno.EBADF:
        #         raise


# def pid_exists(pid):
#     try:
#         os.kill(pid, 0)
#     except OSError as ex:
#         if ex.errno == errno.ESRCH:
#             # This pid has no matching process
#             return False
#     return True


def _read_pidfile(fp):
    fp.seek(0)
    pid_str = fp.read(16).split("\n", 1)[0].strip()
    if not pid_str:
        return None
    return int(pid_str)


# def _flock(fileno):
#     fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)
