##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from itertools import islice
import logging
from AccessControl import getSecurityManager
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.decorators import info


log = logging.getLogger('zen.JobsFacade')


class JobsFacade(ZuulFacade):

    @info
    def getJobs(self, start=0, limit=50, sort='scheduled', dir='ASC',
                createdBy=None):
        start = max(start, 0)
        if limit is None:
            stop = None
        else:
            stop = start + limit
        kwargs = dict(sort_on=sort, sort_order='descending' if dir=='DESC' else 'ascending')
        if createdBy:
            kwargs['user'] = createdBy
        brains = self._dmd.JobManager.getCatalog()(
            **kwargs
        )
        total = len(brains)
        results = islice(brains, start, stop)
        return [b.getObject() for b in results], total

    def abortJob(self, id_):
        self._dmd.JobManager.getJob(id_).abort()

    def deleteJob(self, id_):
        self._dmd.JobManager.deleteJob(id_)

    def getJobDetail(self, id_):
        job = self._dmd.JobManager.getJob(id_)
        try:
            with open(job.logfile, 'r') as f:
                buffer = f.readlines()
                return job.logfile, buffer[-100:], len(buffer) > 100
                
        except (IOError, AttributeError):
            return ("The log file for this job either does not exist or "
                    "cannot be accessed."), (), None

    @info
    def getUserJobs(self):
        user = getSecurityManager().getUser()
        if not isinstance(user, basestring):
            user = user.getId()
        results = self._dmd.JobManager.getCatalog()(user=user)
        return [b.getObject() for b in results]
