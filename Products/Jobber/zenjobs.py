##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import signal
from datetime import datetime

from zope.component import getUtility

import Globals
from Products.ZenUtils.Utils import zenPath, monkeypatch, varPath
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
from Products.ZenUtils.celeryintegration import constants, states, current_app
from Products.ZenUtils.celeryintegration.worker import CeleryZenWorker

from celery import concurrency
from celery.signals import task_prerun
from celery.exceptions import SystemTerminate

from billiard import freeze_support

from Products.Jobber.exceptions import NoSuchJobException
from Products.Jobber.jobs import JobAborted


class CeleryZenJobs(ZenDaemon):

    mname = 'zenjobs'  # For logging

    def __init__(self, *args, **kwargs):
        ZenDaemon.__init__(self, *args, **kwargs)
        self.setup_celery()

    def setup_celery(self):
        current_app.main = self.mname
        current_app.db_options = self.options
        current_app.add_defaults({
            constants.NUM_WORKERS: self.options.num_workers,
            constants.MAX_TASKS_PER_PROCESS: self.options.max_jobs_per_worker,
        })

    def run(self):
        self.log.info('Daemon %s starting up', type(self).__name__)
        freeze_support()
        kwargs = {}
        if self.options.daemon:
            kwargs['logfile'] = zenPath('log', 'zenjobs.log')
        kwargs['loglevel'] = self.options.logseverity
        kwargs["pool_cls"] = concurrency.get_implementation(
                    kwargs.get("pool_cls") or current_app.conf.CELERYD_POOL)
        CeleryZenWorker.daemon = self
        self.worker = CeleryZenWorker(**kwargs)
        self.worker.run()  # blocking call
        #very specific to zenjobs, sigTerm usually called by signal handling
        # or the twisted reactor stopping. Celery handles all signals and
        # reactor is not running, so we explicitly call sigTerm method that
        # cleans up after the daemon.
        self.sigTerm()
        self.log.info('Daemon %s has shut down', type(self).__name__)

    def buildOptions(self):
        """
        Adds our command line options to ZCmdBase command line options.
        """
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--job-log-path', dest='job_log_path',
            default=varPath("log", "jobs"),
            help='Directory in which to store individual job log files')
        self.parser.add_option('--max-jobs-per-worker',
            dest='max_jobs_per_worker', type='int', default=1,
            help='Number of jobs a worker process runs before it shuts down')
        self.parser.add_option('--concurrent-jobs',
            dest='num_workers', type='int', default=2,
            help='Number of jobs to process concurrently')
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)


# Replace the _log_error implementation to ignore JobAborted exceptions.
# This avoids writing exception tracebacks into the log for aborted jobs.
@monkeypatch("celery.worker.job.Request")
def _log_error(self, exc_info):
    if not isinstance(exc_info.exception, JobAborted):
        original(self, exc_info)


@task_prerun.connect
def task_prerun_handler(signal=None, sender=None,
        task_id=None, task=None, args=None, kwargs=None):
    try:
        status = task.app.backend.get_status(task_id)
    except NoSuchJobException:
        # Job hasn't been created yet
        status = None
    if status != states.ABORTED:
        task.app.backend.update(
            task_id, status=states.STARTED, date_started=datetime.utcnow()
        )


if __name__ == "__main__":
    zj = CeleryZenJobs()
    zj.run()
