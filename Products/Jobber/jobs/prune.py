##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from datetime import datetime
from .job import Job


class PruneJob(Job):
    """Prune old jobs in the job catalog."""

    name = "Products.Jobber.PruneJob"

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Prune Job"

    @classmethod
    def getJobDescription(cls, **kwargs):
        """Return a description of the job."""
        return "Prune jobs older than %s" % kwargs["untiltime"]

    def _run(self, untiltime, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.log.info("Prune jobs older than %s " % untiltime)
        self.dmd.JobManager.deleteUntil(untiltime)
        self.dmd.JobManager.lastPruneTime = datetime.now()
