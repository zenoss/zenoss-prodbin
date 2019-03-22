##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from AccessControl import getSecurityManager
from Products.Zuul.facades import ZuulFacade

log = logging.getLogger('zen.JobsFacade')


class JobsFacade(ZuulFacade):
    """Facade for JobManager."""

    def queryJobs(
        self, start=0, limit=50, sort='created', dir='ASC', createdBy=None,
    ):
        start = max(start, 0)
        queryArgs = {
            "key": sort,
            "reverse": (dir == "DESC"),
            "offset": start,
            "limit": limit,
        }
        if createdBy is not None:
            queryArgs["criteria"] = {"userid": createdBy}
        log.debug("queryArgs %s", queryArgs)
        result = self._dmd.JobManager.query(**queryArgs)
        return result["jobs"], result["total"]

    def getJob(self, jobid):
        return self._dmd.JobManager.getJob(jobid)

    def abortJob(self, jobid):
        job = self._dmd.JobManager.getJob(jobid)
        job.abort()

    def deleteJob(self, jobid):
        self._dmd.JobManager.deleteJob(jobid)

    def getJobLog(self, jobid):
        job = self._dmd.JobManager.getJob(jobid)
        try:
            with open(job.logfile, 'r') as f:
                _buffer = f.readlines()
                return job.logfile, _buffer[-100:], len(_buffer) > 100
        except (IOError, AttributeError):
            return ((
                "The log file for this job either does not exist or "
                "cannot be accessed."
            ), (), None)

    def getUserJobs(self):
        user = getSecurityManager().getUser()
        if not isinstance(user, basestring):
            user = user.getId()
        return self._dmd.JobManager.query(criteria={"userid": user})["jobs"]
