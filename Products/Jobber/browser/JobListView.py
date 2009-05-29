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

import time
from itertools import chain
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.ZenUtils.Utils import relative_time, readable_time
from Products.ZenUtils.json import json


class JobListView(BrowserView):
    """
    Show which jobs are running.
    """
    __call__ = ZopeTwoPageTemplateFile('joblist.pt')
    # Give the template object an id so that the tab will be selected
    __call__.id = 'joblist'

    def start_daemon(self):
        self.context.dmd.About.doDaemonAction('zenjobs', 'start')
        self.request.response.redirect('/zport/dmd/JobManager/joblist')
        self.context.callZenScreen(self.request)

    def daemonstr(self):
        pid = self.context.dmd.About._getDaemonPID('zenjobs')
        if pid:
            return "zenjobs daemon is running."
        else:
            return ("zenjobs daemon is not running. "
                   "<a href='startzenjobs'>Start zenjobs</a>")

    def _get_jobs(self):
        jm = self.context.dmd.JobManager.primaryAq()
        pending = jm.getPendingJobs()
        running = jm.getRunningJobs()
        finished = jm.getFinishedJobs()
        return dict(Pending=pending, Running=running, Finished=finished)

    def jobs(self):
        def job_link(jobstatus):
            desc = '%s %s' % (jobstatus.getJob().getJobType(),
                              jobstatus.getJob().getDescription())
            link = jobstatus.absolute_url_path() + '/viewlog'
            return dict(description=desc, link=link)
        _jobs = self._get_jobs()
        return dict(pending=map(job_link, _jobs['pending']),
                    running=map(job_link, _jobs['running']),
                    finished=map(job_link, _jobs['finished']))

    @json
    def jsonjobs(self):
        jobs = self._get_jobs()
        result = dict(jobs=[], total=0)
        def _statstring(state, job):
            if state!='Finished':
                return state
            if job.result:
                return 'Failed'
            return 'Succeeded'
        for k, jobset in jobs.items():
            for job in jobset:
                j = job.getJob()
                # Ignore broken jobs; they get cleaned up in a
                # migrate script
                if j is None: continue
                started, finished = job.getTimes()
                duration = job.getDuration()
                d = dict(
                    status = _statstring(k, job),
                    type = j.getJobType(),
                    description = j.getDescription(),
                    baseurl = job.absolute_url_path()
                )
                if started:
                    d['started']  = relative_time(started)
                d['starttime'] = started and started or (time.time() + 100000)
                if finished: d['finished'] = relative_time(finished)
                if duration: d['duration'] = readable_time(duration)
                result['jobs'].append(d)
                result['total'] += 1
        def cmpjobs(a, b):
            return int(b['starttime']) - int(a['starttime'])
        result['jobs'].sort(cmpjobs)
        return result


