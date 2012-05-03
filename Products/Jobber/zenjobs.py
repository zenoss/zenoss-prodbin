###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals
from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.celeryintegration import reconfigure_celery
from Products.ZenUtils.celeryintegration import constants, states
from celery import concurrency
from celery.app.state import current_app
from datetime import datetime
from celery.signals import task_prerun
try:
    from celery.concurrency.processes.forking import freeze_support
except ImportError:
    freeze_support = lambda *_: None


class CeleryZenJobs(ZenDaemon):

    def __init__(self, *args, **kwargs):
        ZenDaemon.__init__(self, *args, **kwargs)
        self.setup_celery()

    def setup_celery(self):
        self.celery = current_app
        self.celery.db_options = self.options
        reconfigure_celery({
            constants.NUM_WORKERS: self.options.num_workers,
            constants.MAX_TASKS_PER_PROCESS: self.options.max_jobs_per_worker,
        })

    def run(self):
        freeze_support()
        kwargs = {}
        if self.options.daemon:
            kwargs['logfile'] = zenPath('log', 'zenjobs.log')
        kwargs['loglevel'] = self.options.logseverity
        kwargs["pool_cls"] = concurrency.get_implementation(
                    kwargs.get("pool_cls") or self.celery.conf.CELERYD_POOL)
        return self.celery.Worker(**kwargs).run()

    def buildOptions(self):
        """
        Adds our command line options to ZCmdBase command line options.
        """
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--job-log-path', dest='job_log_path',
            default=zenPath("log", "jobs"),
            help='Directory in which to store individual job log files')
        self.parser.add_option('--max-jobs-per-worker',
            dest='max_jobs_per_worker', type='int', default=1,
            help='Number of jobs a worker process runs before it shuts down')
        self.parser.add_option('--concurrent-jobs',
            dest='num_workers', type='int', default=2,
            help='Number of jobs to process concurrently')


@task_prerun.connect
def task_prerun_handler(signal=None, sender=None, task_id=None, task=None, args=None,
                        kwargs=None):
    task.app.backend.update(task_id, status=states.STARTED, date_started=datetime.utcnow())


if __name__ == "__main__":
    zj = CeleryZenJobs()
    zj.run()



class ZenJobs(object):
    """
    Retained for backwards compatibility. Will be removed in the release after
    4.2.
    """

