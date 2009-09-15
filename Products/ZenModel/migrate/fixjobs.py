###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate
import logging
from Products.Jobber.status import JobStatus

log = logging.getLogger('Zope')
ORIG_LEVEL = log.level
HIGHER_THAN_CRITICAL = 100

class FixBadJobs(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        # Hide log messages, since the only ones that can appear here are both
        # scary and irrelevant
        log.setLevel(HIGHER_THAN_CRITICAL)

        # Monkeypatch status.py to avoid syncing from the database
        # and losing the current transaction state
        def substituteMethod( self ):
            return self.filename

        originalMethod = JobStatus.getLogFileName
        JobStatus.getLogFileName = substituteMethod

        try:
            try:
                for status in dmd.JobManager.jobs():
                    if hasattr(status, 'job'):
                        status.delete()
            except:
                # If we run into trouble, turn logging back on
                log.setLevel(ORIG_LEVEL)
                raise
        finally:
            # Put the original method back
            JobStatus.getLogFileName = originalMethod

        # Set the log level back to normal
        log.setLevel(ORIG_LEVEL)

FixBadJobs()
