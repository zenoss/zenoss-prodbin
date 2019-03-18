##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from Products.ZenUtils.Utils import ThreadInterrupt


class JobAborted(ThreadInterrupt):
    """The job has been aborted."""


class NoSuchJobException(Exception):
    """No such job exists."""


class JobAlreadyExistsException(Exception):
    """A matching job has already been submitted, and is not yet finished."""


class SubprocessJobFailed(Exception):
    """A subprocess job exited with a non-zero return code."""

    def __init__(self, exitcode):
        """Initialize a SubprocessJobFailed exception."""
        self.exitcode = exitcode


class FacadeMethodJobFailed(Exception):
    """A facade method job failed."""
