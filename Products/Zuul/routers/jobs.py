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
"""
Operations for jobs.

Available at: /zport/dmd/jobs_router
"""

import logging
from time import mktime
from datetime import datetime
from collections import defaultdict
from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.ZenMessaging.audit import audit
from Products.Jobber.exceptions import NoSuchJobException

log = logging.getLogger('zen.JobsRouter')


JOBKEYS = ['uuid', 'type', 'description', 'scheduled', 'started', 'finished',
           'status', 'user']


class JobsRouter(DirectRouter):
    """
    A JSON/Ext.Direct interface to operations on jobs
    """
    def __init__(self, context, request):
        self.api = Zuul.getFacade('jobs', context.dmd)
        self.context = context
        self.request = request
        super(DirectRouter, self).__init__(context, request)

    def getJobs(self, start, limit, page, sort, dir, uid=None):
        # if user isn't global only show them the jobs they created
        user = self.context.dmd.ZenUsers.getUserSettings()
        createdBy = user.id if user.hasNoGlobalRoles() else None

        jobs, total = self.api.getJobs(start=start, limit=limit, sort=sort, dir=dir, createdBy=createdBy)
        return DirectResponse(jobs=Zuul.marshal(jobs, keys=JOBKEYS), totalCount=total)

    def abort(self, jobids):
        for id_ in jobids:
            try:
                self.api.abortJob(id_)
            except NoSuchJobException:
                log.debug("Unable to abort job: %s No such job found.", id_)

    def deleteJobs(self, jobids):
        for id_ in jobids:
            try:
                self.api.deleteJob(id_)
            except NoSuchJobException:
                log.debug("Unable to delete job: %s No such job found.", id_)

    def detail(self, jobid):
        try:
            logfile, content, maxLimit = self.api.getJobDetail(jobid)
        except NoSuchJobException:
            # Probably a detail request overlapped a delete request. Just
            # return None.
            logfile, content, maxLimit = None, None, None
        return {'content': content, 'logfile': logfile, 'maxLimit' : maxLimit}

    def userjobs(self):
        results = defaultdict(list)
        totals = {}
        validstates = {'STARTED':'started', 'SUCCESS':'finished',
                       'PENDING':'scheduled'}
        for job in self.api.getUserJobs():
            if job.status in validstates:
                results[job.status].append(job)
        # Sort and slice appropriately -- most recent 10 items
        for status, jobs in results.iteritems():
            jobs.sort(key=lambda j:getattr(j, validstates[status]),
                      reverse=True)
            totals[status] = len(jobs)
            results[status] = jobs[:10]
        return DirectResponse(jobs=Zuul.marshal(results, keys=JOBKEYS),
                              totals=totals)
