##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
from datetime import datetime
from zope.component import getUtility
from Products.ZenUtils.Utils import zenPath, monkeypatch
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.celeryintegration import reconfigure_celery
from Products.ZenUtils.celeryintegration import constants, states
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
from celery import concurrency
from celery.app.state import current_app
from celery.signals import task_prerun
try:
    from celery.concurrency.processes.forking import freeze_support
except ImportError:
    freeze_support = lambda *_: None

from Products.Jobber.exceptions import NoSuchJobException
from Products.Jobber.jobs import JobAborted


class CeleryZenJobs(ZenDaemon):

    mname = 'zenjobs'  # For logging

    def __init__(self, *args, **kwargs):
        ZenDaemon.__init__(self, *args, **kwargs)
        self.setup_celery()

    def setup_celery(self):
        self.celery = current_app
        self.celery.db_options = self.options
        reconfigure_celery({
            constants.NUM_WORKERS: self.options.num_workers,
            constants.MAX_TASKS_PER_PROCESS: self.options.max_jobs_per_worker,

            # Configure the value of the 'CELERYD_POOL_PUTLOCKS'.  When
            # True, it causes a temporary deadlock to occur during shutdown
            # when all workers are busy and there exists at least one
            # pending job. The deadlock is broken when a worker completes
            # its job. Setting 'CELERYD_POOL_PUTLOCKS' to False allows
            # shutdown to occur without waiting.
            "CELERYD_POOL_PUTLOCKS": False,
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
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)


# Wrap the WorkController._shutdown() method to set the 'warm' parameter
# to False.  The 'warm' parameter controls whether workers wait for their
# tasks to complete before exiting (warm=True) or exit without waiting for
# the tasks to complete (warm=False).
@monkeypatch("celery.worker.WorkController")
def _shutdown(self, warm=True):
    # 'original' is a reference to the original _shutdown method.
    # (injected by monkeypatch decorator)
    return original(self, warm=False)


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


class ZenJobs(object):
    """
    Retained for backwards compatibility. Will be removed in the release after
    4.2.
    """
