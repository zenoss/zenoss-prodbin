###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from itertools import islice
import logging
from AccessControl import getSecurityManager
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.decorators import info


log = logging.getLogger('zen.JobsFacade')


class JobsFacade(ZuulFacade):

    @info
    def getJobs(self, start=0, limit=50, sort='scheduled', dir='ASC',
                query=None):
        start = max(start, 0)
        if limit is None:
            stop = None
        else:
            stop = start + limit
        brains = self._dmd.JobManager.getCatalog()(
            sort_on=sort, sort_limit=stop,
            sort_order='descending' if dir=='DESC' else 'ascending'
        )
        total = len(brains)
        results = islice(brains, start, stop)
        return [b.getObject() for b in results], len(brains)

    def abortJob(self, id_):
        self._dmd.JobManager.getJob(id_).abort()

    def deleteJob(self, id_):
        self._dmd.JobManager.deleteJob(id_)

    def getJobDetail(self, id_):
        job = self._dmd.JobManager.getJob(id_)
        try:
            with open(job.logfile, 'r') as f:
                return job.logfile, f.readlines()[-100:]
        except (IOError, AttributeError):
            return ("The log file for this job either does not exist or "
                    "cannot be accessed."), ()

    @info
    def getUserJobs(self):
        user = getSecurityManager().getUser()
        if not isinstance(user, basestring):
            user = user.getId()
        results = self._dmd.JobManager.getCatalog()(user=user)
        return [b.getObject() for b in results]
