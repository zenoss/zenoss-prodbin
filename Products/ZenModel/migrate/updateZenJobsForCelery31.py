##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.Jobber.manager import manage_addJobManager, JOBMANAGER_VERSION
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION  # noqa: E501

import Migrate

log = logging.getLogger("zen.migrate")


class UpdateZenJobsForCelery31(Migrate.Step):
    """Updates zenjobs related stuff for redis and Celery v3.1.26."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        prior_version = getattr(dmd.JobManager, "_jobmanager_version", 1)
        if prior_version < JOBMANAGER_VERSION:
            count = self._log_unfinished_jobs(dmd)
            log.info(
                "Removing old JobManager%s.",
                "" if count == 0 else " and %s unfinished jobs" % count,
            )
            try:
                del dmd.JobManager
            except Exception:
                dmd._delOb("JobManager")
            log.info(
                "Old JobManager%s removed.",
                "" if count == 0 else " and %s unfinished jobs" % count,
            )
            manage_addJobManager(dmd)
            log.info("New JobManager added.")
        else:
            log.info("New JobManager already added.")

    def _log_unfinished_jobs(self, dmd):
        jobs = list(dmd.JobManager.getUnfinishedJobs())
        if not jobs:
            log.info("No unfinished jobs found.")
            return 0
        log.info("Found %s unfinished jobs", len(jobs))
        for job in jobs:
            log.info(".. %s %s %s", job.type, job.job_name, job.description)
        return len(jobs)


UpdateZenJobsForCelery31()
