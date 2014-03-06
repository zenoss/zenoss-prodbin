##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import sys
import os
import time
import logging
import Queue
import errno
import signal
import traceback
import subprocess

import transaction
from AccessControl.SecurityManagement import (
        newSecurityManager, noSecurityManager
    )
from Products.CMFCore.utils import getToolByName
from ZODB.transact import transact

from Products.ZenUtils.Utils import (
        InterruptableThread, ThreadInterrupt, LineReader
    )
from Products.ZenUtils.celeryintegration import (
        current_app, Task, states, get_task_logger
    )

from .exceptions import NoSuchJobException, SubprocessJobFailed

_MARKER = object()


class JobAborted(ThreadInterrupt):
    """
    The job has been aborted.
    """


class SubJob(object):
    """
    Container for a job invocation.  Use the Job.makeSubJob method to create
    instances of this class.
    """

    def __init__(self, job,
            args=None, kwargs=None, description=None, options={}):
        """
        Initialize an instance of SubJob.

        The supported options are:
            immutable - {bool} Set True to 'freeze' the job's arguments.
            ignoreresult - {bool} Set True to drop the result of the job.

        @param job {Job} The job instance to execute.
        @param args {sequence} Arguments to pass to the job.
        @param kwargs {dict} Keyword/value arguments to pass to the job.
        @param description {str} Description of job (for JobRecord)
        @options {dict} Options to control the job.
        """
        self.job = job
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.description = description
        self.options = options.copy()


class Job(Task):
    """
    Base class for jobs.
    """
    abstract = True  # Job class itself is not registered.
    initialize_timeout = 30  # seconds
    _runner_thread = None
    _aborter_thread = None
    _result_queue = Queue.Queue()
    _log = None
    _aborted_tasks = set()
    acks_late = True
    _origsigtermhandler = None

    @classmethod
    def getJobType(cls):
        """
        """
        return cls.name

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """
        This is expected to be overridden in subclasses for nice descriptions.
        """
        raise NotImplementedError

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """
        Return a SubJob instance that wraps the given job and its arguments
        and options.
        """
        job = current_app.tasks[cls.name]
        return SubJob(job, args=args, kwargs=kwargs,
                description=description, options=options)

    def setProperties(self, **properties):
        self.app.backend.update(self.request.id, **properties)

    def _get_config(self, key, default=_MARKER):
        opts = getattr(self.app, 'db_options', None)
        sanitized_key = key.replace("-", "_")
        value = getattr(opts, sanitized_key, _MARKER)
        if value is _MARKER:
            raise ValueError("Config option %s is not defined" % key)
        return value

    @property
    def log(self):
        if self._log is None:
            # Get log directory, ensure it exists
            logdir = self._get_config('job-log-path')
            try:
                os.makedirs(logdir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            # Make the logfile path and store it in the backend for later
            # retrieval
            logfile = os.path.join(logdir, '%s.log' % self.request.id)
            self.setProperties(logfile=logfile)
            self._log = get_task_logger(self.request.id)
            self._log.setLevel(self._get_config('logseverity'))
            handler = logging.FileHandler(logfile)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s zen.Job: %(message)s"))
            self._log.handlers = [handler]
        return self._log

    @property
    def dmd(self):
        """
        Gets the dmd object from the backend
        """
        return self.app.backend.dmd

    def _wait_for_pending_job(self, job_id):
        i = 0
        # Exactly one job executes at a time, so it's fine to block waiting
        # for the database to get the pending job.
        jmgr = self.dmd.JobManager
        while i < self.initialize_timeout:
            try:
                jmgr._p_jar.sync()
                return jmgr.getJob(job_id)
            except NoSuchJobException:
                i += 1
                time.sleep(1)
        raise NoSuchJobException(job_id)

    def _check_aborted(self, job_id):
        try:
            while True:
                self.dmd._p_jar.sync()
                try:
                    status = self.app.backend.get_status(job_id)
                except NoSuchJobException:
                    status = states.ABORTED
                if status == states.ABORTED and \
                        self._runner_thread is not None:
                    self.log.info("Job %s is aborted", job_id)
                    # Sometimes the thread is about to commit before it
                    # can get interrupted.  self._aborted_tasks is an
                    # in-memory shared set so other thread can check on
                    # it before it commits.
                    self._aborted_tasks.add(job_id)
                    self._runner_thread.interrupt(JobAborted)
                    break
                time.sleep(0.25)
        finally:
            # release database connection acquired by the self.dmd
            # reference ealier in this method.
            self.backend.reset()

    def _do_run(self, request, args=None, kwargs=None):
        # This method runs a separate thread.
        args = args or ()
        kwargs = kwargs or {}
        job_id = request.id
        job_record = self.dmd.JobManager.getJob(job_id)
        # Log in as the job's user
        self.log.debug("Logging in as %s", job_record.user)
        utool = getToolByName(self.dmd.getPhysicalRoot(), 'acl_users')
        user = utool.getUserById(job_record.user)
        if user is None:
            user = self.dmd.zport.acl_users.getUserById(job_record.user)
        user = user.__of__(utool)
        newSecurityManager(None, user)

        @transact
        def _runjob():
            result = self._run(*args, **kwargs)
            if job_id in self._aborted_tasks:
                raise JobAborted("Job %s aborted" % job_id)
            return result

        # Run it!
        self.log.info("Starting job %s (%s)", job_id, self.name)
        try:
            # Make request available to self.request property
            # (because self.request is thread local)
            self.request_stack.push(request)
            try:
                result = _runjob()
                self.log.info(
                    "Job %s finished with result %s", job_id, result
                )
                self._result_queue.put(result)
            except JobAborted:
                self.log.warning("Job %s aborted.", job_id)
                transaction.abort()
                # re-raise JobAborted to allow celery to perform job
                # failure and clean-up work.  A monkeypatch has been
                # installed to prevent this exception from being written to
                # the log.
                raise
        except Exception as e:
            e.exc_info = sys.exc_info()
            self._result_queue.put(e)
        finally:
            # Remove the request
            self.request_stack.pop()
            # Log out; probably unnecessary but can't hurt
            noSecurityManager()
            self._aborted_tasks.discard(job_id)
            # release database connection acquired by the self.dmd
            # reference ealier in this method.
            self.backend.reset()

    def run(self, *args, **kwargs):
        job_id = self.request.id
        self.log.info("Job %s (%s) received", job_id, self.name)
        self.log.debug("Waiting for job %s to appear in database", job_id)
        try:
            # Wait for the job to appear in the database.
            self._wait_for_pending_job(job_id)
        except NoSuchJobException:
            # Timed out waiting for job.
            try:
                # This may also fail because the job was deleted before
                # being read from the queue.
                self.update_state(state=states.ABORTED)
            except Exception:
                self.log.debug("No such job %s found in database", job_id)
            return
        self.log.debug("Job %s found in database", job_id)

        self._aborter_thread = InterruptableThread(
                target=self._check_aborted, args=(job_id,)
            )
        # Forward the request to the thread because the self.request
        # property is a thread-local value.
        self._runner_thread = InterruptableThread(
                target=self._do_run, args=(self.request,),
                kwargs={'args': args, 'kwargs': kwargs}
            )

        try:
            # Install a SIGTERM handler so that the 'runner_thread' can be
            # interrupted/aborted when the TERM signal is received.
            self._origsigtermhandler = signal.signal(
                    signal.SIGTERM, self._sigtermhandler
                )

            self._runner_thread.start()
            self._aborter_thread.start()

            # A blocking join() call also blocks the thread from calling
            # signal handlers, so use a timeout join and loop until the
            # thread exits to allow the thread an opportunity to call
            # signal handlers.
            self.log.debug("Monitoring _runner_thread existence")
            while self._runner_thread.is_alive():
                self._runner_thread.join(0.01)
            self.log.debug("_runner_thread has exited")

            result = self._result_queue.get_nowait()
            if isinstance(result, Exception):
                cls, instance, tb = result.exc_info[0:3]
                if not isinstance(result, JobAborted):
                    self.log.error("Job %s failed with an exception" % job_id)
                    message = traceback.format_exc( tb)
                    self.log.error(message)
                links = []
                if self.request.callbacks:
                    for callback in self.request.callbacks:
                        links.extend(callback.flatten_links())
                for link in links:
                    link.type.update_state(
                        task_id=link.options['task_id'],
                        state=states.ABORTED
                    )
                if links:
                    self.log.info(
                        "Dependent job(s) %s aborted",
                        ', '.join(link.options['task_id'] for link in links)
                    )
                raise cls, instance, tb

            return result
        except Queue.Empty:
            return None
        finally:
            # Remove our signal handler and re-install the original handler
            if signal.getsignal(signal.SIGTERM) == self._sigtermhandler:
                signal.signal(signal.SIGTERM, self._origsigtermhandler)
            # Kill the aborter
            try:
                self._aborter_thread.kill()
                self._aborter_thread.join(0.5)
            except ValueError:
                pass
            # Clean up the logger
            try:
                del self._log.logger.manager.loggerDict[self.request.id]
            except (AttributeError, KeyError):
                pass
            self._log = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Because JobAborted is an exception, celery will change the state to
        # FAILURE once the task completes. Since we want it to remain ABORTED,
        # we'll set it back here.
        if isinstance(exc, JobAborted):
            self.update_state(state=states.ABORTED)

    def _run(self, *args, **kwargs):
        raise NotImplementedError("_run must be implemented")

    def _sigtermhandler(self, signum, frame):
        self.log.debug("%s received signal %s", self, signum)
        # Interrupt the runner_thread.
        self._runner_thread.interrupt(JobAborted)
        # Wait for the runner_thread to exit.
        while self._runner_thread.is_alive():
            time.sleep(0.01)
        # Install the original SIGTERM handler
        signal.signal(signal.SIGTERM, self._origsigtermhandler)
        # Send this process a SIGTERM signal
        os.kill(os.getpid(), signal.SIGTERM)


class SubprocessJob(Job):

    @classmethod
    def getJobType(cls):
        return "Shell Command"

    @classmethod
    def getJobDescription(cls, cmd, environ=None):
        return cmd if isinstance(cmd, basestring) else ' '.join(cmd)

    def _run(self, cmd, environ=None):
        self.log.debug("Running Job %s %s", self.getJobType(), self.name)
        if environ is not None:
            newenviron = os.environ.copy()
            newenviron.update(environ)
            environ = newenviron
        process = None
        exitcode = None
        handler = self.log.handlers[0]
        originalFormatter = handler.formatter
        lineFormatter = logging.Formatter('%(message)s')
        try:
            self.log.info("Spawning subprocess: %s", SubprocessJob.getJobDescription(cmd))
            process = subprocess.Popen(cmd, bufsize=1, env=environ,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)

            # Since process.stdout.readline() is a blocking call, it stops
            # the injected exception from being raised until it unblocks.
            # The LineReader object allows non-blocking readline()
            # behavior to avoid delaying the injected exception.
            reader = LineReader(process.stdout)
            reader.start()
            # Reset the log message formatter (restored later)
            while exitcode is None:
                line = reader.readline()
                if line:
                    try:
                        handler.setFormatter(lineFormatter)
                        self.log.info(line.strip())
                    finally:
                        handler.setFormatter(originalFormatter)
                else:
                    exitcode = process.poll()
                    time.sleep(0.1)
        except JobAborted:
            if process:
                self.log.warn("Job aborted. Killing subprocess...")
                process.kill()
                process.wait()  # clean up the <defunct> process
                self.log.info("Subprocess killed.")
            raise
        if exitcode != 0:
            raise SubprocessJobFailed(exitcode)
        return exitcode
