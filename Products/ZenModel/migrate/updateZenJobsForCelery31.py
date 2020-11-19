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
        try:
            prior_version = getattr(dmd, "JobManager")
        except TypeError:
            log.info("Removing old JobManager.")
            try:
                del dmd.JobManager
            except Exception:
                dmd._delOb("JobManager")
            log.info("Old JobManager removed.")
            manage_addJobManager(dmd)
            log.info("New JobManager added.")
        else:
            log.info("New JobManager already added.")

UpdateZenJobsForCelery31()
