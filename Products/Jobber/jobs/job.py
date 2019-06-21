##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import errno
import logging
import os
import signal
import six
import traceback
import sys
import transaction

from AccessControl.SecurityManagement import (
    newSecurityManager,
    noSecurityManager,
)
from celery.exceptions import Ignore
from Products.CMFCore.utils import getToolByName
from ZODB.transact import transact
from zope.component import getUtility

import Products.ZenUtils.guid as guid

from Products.ZenEvents import Event
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenUtils.Threading import InterruptableThread
from Products.ZenUtils.celeryintegration import (
    current_app,
    Task,
    states,
    get_task_logger,
)

from ..exceptions import NoSuchJobException, JobAborted, TaskAborted

_MARKER = object()


class Job(Task):
    """Base class for jobs."""

    abstract = True  # Job class itself is not registered.

    _signum = None
    _log = None
    acks_late = True
    _original_sigterm_handler = None

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job.

        By default, the class type name is returned.
        """
        return cls.name

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """Return a description of the job.

        The description can be specific to the job instance.
        This must be overridden by subclasses.
        """
        raise NotImplementedError

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """Return a celery.canvas.Signature instance.

        The Signature instance wraps the given job, its arguments, and options.
        """
        task = current_app.tasks[cls.name]
        opts = dict(options)
        if description:
            opts["description"] = description
        args = args or ()
        kwargs = kwargs or {}
        return task.s(*args, **kwargs).set(**opts)

    def setProperties(self, **properties):
        """Apply key/value pairs to the JobRecord."""
        self.app.backend.update(self.request.id, **properties)

    def _get_config(self, key, default=_MARKER):
        opts = getattr(self.app, "db_options", None)
        sanitized_key = key.replace("-", "_")
        value = getattr(opts, sanitized_key, _MARKER)
        if value is _MARKER:
            raise ValueError("Config option %s is not defined" % key)
        return value

    @property
    def log(self):
        """Return the logger for this job."""
        if self._log is None:
            # Get log directory, ensure it exists
            logdir = self._get_config("job-log-path")
            try:
                os.makedirs(logdir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            # Make the logfile path and store it in the backend for later
            # retrieval
            logfile = os.path.join(logdir, "%s.log" % self.request.id)
            self.setProperties(logfile=logfile)
            self._log = get_task_logger(self.request.id)
            self._log.setLevel(self._get_config("logseverity"))
            handler = logging.FileHandler(logfile)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s zen.Job: %(message)s",
            ))
            self._log.handlers = [handler]
        return self._log

    @property
    def dmd(self):
        """Return current dmd instance."""
        return self.app.backend.dmd

    def _is_aborted(self, jobid):
        self.dmd._p_jar.sync()
        try:
            status = self.app.backend.get_status(jobid)
        except NoSuchJobException:
            status = states.ABORTED
        return status == states.ABORTED

    def run(self, *args, **kwargs):
        """Execute the job."""
        try:
            # Ignore the job if it's already aborted.
            jobid = self.request.id
            if self._is_aborted(jobid):
                self.log.info("Ignoring aborted job: %s", jobid)
                raise Ignore()

            runner = JobRunner(self, self.request, args, kwargs)
            runner.start()

            # Install signal handlers.
            self._original_sigterm_handler = signal.signal(
                signal.SIGTERM, self._sighandler,
            )
            self._original_sigint_handler = signal.signal(
                signal.SIGINT, self._sighandler,
            )

            interrupted = False
            while True:
                if not runner.is_alive():
                    self.log.debug("Job runner has exited")
                    break
                if not interrupted and self._is_aborted(jobid):
                    self.log.warning("Aborting job")
                    runner.interrupt(JobAborted)
                    interrupted = True
                runner.join(0.1)

            if not isinstance(runner.result, BaseException):
                return runner.result

            links = []
            if self.request.callbacks:
                for callback in self.request.callbacks:
                    links.extend(callback.flatten_links())
            for link in links:
                link.type.update_state(
                    task_id=link.options["task_id"],
                    state=states.ABORTED,
                )
            if links:
                self.log.info(
                    "Dependent job(s) %s aborted",
                    ", ".join(link.options["task_id"] for link in links),
                )

            if isinstance(runner.result, JobAborted):
                _, _, tb = runner.result.exc_info[0:3]
                raise TaskAborted, TaskAborted(), tb

            # Job finished with an exception, so re-raise it from here
            cls, instance, tb = runner.result.exc_info[0:3]
            raise six.reraise(cls, instance, tb=tb)
        finally:
            # Remove our signal handler and re-install the original handler
            if signal.getsignal(signal.SIGTERM) == self._sighandler:
                signal.signal(signal.SIGTERM, self._original_sigint_handler)
            if signal.getsignal(signal.SIGINT) == self._sighandler:
                signal.signal(signal.SIGINT, self._original_sigint_handler)
            if self._signum:
                signum = self._signum
                self._signum = None
                os.kill(os.getpid(), signum)
            # Clean up the logger
            try:
                del self._log.logger.manager.loggerDict[self.request.id]
            except (AttributeError, KeyError):
                pass
            for handler in self._log.handlers:
                handler.close()
            self._log = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Call to handle job failures."""
        # Because JobAborted is an exception, celery will change the state to
        # FAILURE once the task completes. Since we want it to remain ABORTED,
        # we'll set it back here.
        if isinstance(exc, TaskAborted):
            self.update_state(state=states.ABORTED)

        # Don't send an event when a job is aborted.
        if not isinstance(exc, TaskAborted):
            # Send an event about the job failure.
            publisher = getUtility(IEventPublisher)
            event = Event.buildEventFromDict({
                "device": self.getJobType(),
                "severity": Event.Error,
                "component": "zenjobs",
                "eventClass": "/App/Job/Fail",
                "message": self.getJobDescription(*args, **kwargs),
                "summary": repr(exc),
                "jobid": str(task_id),
            })
            event.evid = guid.generate(1)
            publisher.publish(event)

    def _run(self, *args, **kwargs):
        raise NotImplementedError("_run must be implemented")

    def _sighandler(self, signum, frame):
        self._signum = signum
        self.log.info("%s received signal %s", self, signum)
        self.update_state(state=states.ABORTED)


class JobRunner(InterruptableThread):
    """Execute a Job in a thread."""

    def __init__(self, task, request, args, kwargs):
        self.task = task
        self.request = request
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.log = task.log
        super(JobRunner, self).__init__(name="JobRunner")

    def run(self):
        try:
            # This method runs a separate thread.
            job_id = self.request.id
            dmd = self.task.dmd
            job_record = dmd.JobManager.getJob(job_id)

            # Log in as the job's user
            self.log.debug("Logging in as %s", job_record.user)
            utool = getToolByName(dmd.getPhysicalRoot(), "acl_users")
            user = utool.getUserById(job_record.user)
            if user is None:
                user = dmd.zport.acl_users.getUserById(job_record.user)
            user = user.__of__(utool)
            newSecurityManager(None, user)

            # Push the request onto a thread-local stack.
            self.task.request_stack.push(self.request)

            self.log.info("Job started")
            try:
                run = transact(self.task._run)
                result = run(*self.args, **self.kwargs)
                self.result = result
            except Exception as ex:
                self.log.error("Job failed: %s", ex)
                raise
            except JobAborted:
                self.log.warning("Job aborted")
                # re-raise JobAborted to allow celery to perform job
                # failure and clean-up work.  A monkeypatch has been
                # installed to prevent this exception from being written to
                # the log.
                raise
            else:
                self.log.info("Job finished")
        except BaseException as e:  # catches everything
            e.exc_info = sys.exc_info()
            self.result = e
            transaction.abort()
        finally:
            # Log out; probably unnecessary but can't hurt
            noSecurityManager()
            # release database connection acquired by the self.dmd
            # reference ealier in this method.
            self.task.app.backend.reset()
            # Pop the request from its thread-local stack
            self.task.request_stack.pop()
