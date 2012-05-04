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
import sys
import os
import time
import logging
import Queue

import errno
import subprocess
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.CMFCore.utils import getToolByName
from ZODB.transact import transact

from celery.utils import fun_takes_kwargs

from Products.ZenUtils.Utils import InterruptableThread, ThreadInterrupt
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
                    self._runner_thread.interrupt(JobAborted)
                    break
            time.sleep(0.5)

    def _do_run(self, *args, **kwargs):
        # self.request.id is thread-local, so store this from parent
        if self.request.id is None:
            self.request.id = kwargs.get('task_id')
        try:
            del kwargs['task_id']
        except KeyError: 
            pass

        job_record = self.dmd.JobManager.getJob(self.request.id)

        # Log in as the job's user
        self.log.debug("Logging in as %s" % job_record.user)
        utool = getToolByName(self.dmd.getPhysicalRoot(), 'acl_users')
        user = utool.getUserById(job_record.user)
        if user is None:
            user = self.dmd.zport.acl_users.getUserById(job_record.user)
        user = user.__of__(utool)
        newSecurityManager(None, user)

        # Run it!
        self.log.info("Beginning job")
        try:
            try:
                result = self._run(*args, **kwargs)
                self._result_queue.put(result)
            except JobAborted:
                self.log.warning("Job aborted.")
                raise
        except Exception, e:
            # TODO: possibly swallow JobAborted here; not sure what's best yet
            e.exc_info = sys.exc_info()
            self._result_queue.put(e)
        finally:
            # Log out; probably unnecessary but can't hurt
            noSecurityManager()


    @transact
    def run(self, *args, **kwargs):
        self.log.debug("Job received, waiting for other side to commit")
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
        self._runner_thread.start()
        self._aborter_thread.start()
        try:
            self._runner_thread.join()
            result = self._result_queue.get_nowait()
            if isinstance(result, Exception):
                if not isinstance(result, JobAborted):
                    self.log.error("Job raised exception", result.exc_info[2])
                raise result.exc_info[0], result.exc_info[1], result.exc_info[2]
            return result
        except Queue.Empty:
            return None
        finally:
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


class SubprocessJob(Job):

    @classmethod
    def getJobType(cls):
        return "Shell Command"

    @classmethod
    def getJobDescription(cls, cmd, environ=None):
        return cmd if isinstance(cmd, basestring) else ' '.join(cmd)

    def _run(self, cmd, environ=None):
        if environ is not None:
            newenviron = os.environ.copy()
            newenviron.update(environ)
            environ = newenviron
        self.log.info("Spawning subprocess: %s" % SubprocessJob.getJobDescription(cmd))
        process = subprocess.Popen(cmd, bufsize=1, env=environ,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

        exitcode = None
        while exitcode is None:
            orig = None
            try:
                line = process.stdout.readline()
                if line:
                    handler = self.log.handlers[0]
                    orig = handler.formatter
                    handler.setFormatter(logging.Formatter('%(message)s'))
                    self.log.info(line.strip())
                else:
                    exitcode = process.poll()
                    time.sleep(0.1)
            except JobAborted:
                self.log.error("Job aborted. Killing subprocess...")
                process.kill()
                self.log.info("Subprocess killed.")
                raise
            finally:
                if orig is not None:
                    handler.setFormatter(orig)
        if exitcode != 0:
            raise SubprocessJobFailed(exitcode)


class ShellCommandJob(object):
    """
    Backwards compatibility. Will be removed in the release after 4.2.
    """
