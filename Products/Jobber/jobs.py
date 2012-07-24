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
import subprocess

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.CMFCore.utils import getToolByName
from ZODB.transact import transact

from celery.utils import fun_takes_kwargs

from Products.ZenUtils.Utils import (
        InterruptableThread, ThreadInterrupt, LineReader
    )
from Products.ZenUtils.celeryintegration import Task, states

states.ABORTED = "ABORTED"

from .exceptions import NoSuchJobException, SubprocessJobFailed


_MARKER = object()


class JobAborted(ThreadInterrupt):
    """
    The job has been aborted.
    """


class Job(Task):
    """
    Base class for jobs.
    """
    abstract = True
    initialize_timeout = 30 # seconds
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
        This is expected to be overridden in subclasses for pretty names.
        """
        return cls.__name__

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """
        This is expected to be overridden in subclasses for nice descriptions.
        """
        raise NotImplementedError

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
            self._log = self.get_logger(logger_name=self.request.id)
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

    def _wait_for_pending_job(self):
        i = 0
        # Exactly one job executes at a time, so it's fine to block waiting for
        # the database to get the pending job
        jmgr = self.dmd.JobManager
        while i < self.initialize_timeout:
            try:
                jmgr._p_jar.sync()
                return jmgr.getJob(self.request.id)
            except NoSuchJobException:
                i += 1
                time.sleep(1)
        raise

    def _check_aborted(self, task_id):
        while True:
            self.dmd._p_jar.sync()
            try:
                status = self.backend.get_status(task_id)
            except NoSuchJobException:
                status = states.ABORTED
            if (status == states.ABORTED and self._runner_thread is not None):
                self.log.info("Job %s is aborted", task_id)
                # Sometimes the thread is about to commit before it can get interrupted.
                # self._aborted_tasks is an in-memory shared set so other thread
                # can check on it before it commits.
                self._aborted_tasks.add(task_id)
                self._runner_thread.interrupt(JobAborted)
                break
            time.sleep(0.5)

    @transact
    def _do_run(self, *args, **kwargs):
        # self.request.id is thread-local, so store this from parent
        if self.request.id is None:
            self.request.id = kwargs.get('task_id')
        try:
            del kwargs['task_id']
        except KeyError:
            pass

        job_record = self.dmd.JobManager.getJob(self.request.id)
        job_id = job_record.id
        # Log in as the job's user
        self.log.debug("Logging in as %s" % job_record.user)
        utool = getToolByName(self.dmd.getPhysicalRoot(), 'acl_users')
        user = utool.getUserById(job_record.user)
        if user is None:
            user = self.dmd.zport.acl_users.getUserById(job_record.user)
        user = user.__of__(utool)
        newSecurityManager(None, user)

        # Run it!
        self.log.info("Beginning job %s %s", self.getJobType(), self.name)
        try:
            try:
                result = self._run(*args, **kwargs)
                self.log.info("Job %s Finished with result %s", job_record.id, result)
                if job_id in self._aborted_tasks:
                    self.log.info("Job %s aborted rolling back thread local transaction", job_record.id)
                    import transaction
                    transaction.abort()
                    return
                self._result_queue.put(result)
            except JobAborted:
                self.log.warning("Job aborted.")
                # re-raise JobAborted to allow celery to perform job
                # failure and clean-up work.  A monkeypatch has been
                # installed to prevent this exception from being written to
                # the log.
                raise
        except Exception, e:
            e.exc_info = sys.exc_info()
            self._result_queue.put(e)
        finally:
            # Log out; probably unnecessary but can't hurt
            noSecurityManager()
            self._aborted_tasks.discard(job_id)

    def run(self, *args, **kwargs):
        self.log.info("Job %s %s received, waiting for other side to commit",
            self.getJobType(), self.name)
        try:
            # Wait for the job creator (i.e. the 1%) to complete the
            # transaction, pushing a pending job into the database
            self._wait_for_pending_job()
        except NoSuchJobException:
            # Timed out waiting for the other side to commit, so let's cancel
            # this guy and move on
            self.update_state(state=states.ABORTED)
            return

        # Have to find appropriate kwargs ourselves, because celery accepts
        # everything but only passes into run() what is defined. Since we're
        # inserting a layer we have to do the same.  All of args will be
        # destined for _run(), but we need to filter out things from kwargs
        # that aren't (task_id, task_name, delivery_info, etc.) Luckily celery
        # provides fun_takes_kwargs which figures it out.
        accepted = fun_takes_kwargs(self._run, kwargs)
        d = dict((k, v) for k, v in kwargs.iteritems() if k in accepted)

        self._aborter_thread = InterruptableThread(target=self._check_aborted,
                                                   args=(self.request.id,))
        if not d.get('task_id'):
            d['task_id'] = self.request.id
        self._runner_thread = InterruptableThread(target=self._do_run,
                                                  args=args, kwargs=d)

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
            while self._runner_thread.is_alive():
                self._runner_thread.join(0.01)
            result = self._result_queue.get_nowait()
            if isinstance(result, Exception):
                if not isinstance(result, JobAborted):
                    self.log.error("Job raised exception %s", result.exc_info[2])
                raise result.exc_info[0], result.exc_info[1], result.exc_info[2]

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
        self.log.info("Running Job %s %s", self.getJobType(), self.name)
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
                self.log.error("Job aborted. Killing subprocess...")
                process.kill()
                process.wait()  # clean up the <defunct> process
                self.log.info("Subprocess killed.")
            raise
        if exitcode != 0:
            raise SubprocessJobFailed(exitcode)
        return exitcode


class ShellCommandJob(object):
    """
    Backwards compatibility. Will be removed in the release after 4.2.
    """
