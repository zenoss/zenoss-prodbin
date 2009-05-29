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

class FixBadJobs(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        for status in dmd.JobManager.jobs():
            if hasattr(status, 'job'):
                status.delete()

FixBadJobs()
