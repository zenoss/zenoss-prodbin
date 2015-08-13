##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
import time
import threading
import Queue
import transaction
import logging
import traceback

from zope.component import getUtility
from ZODB.transact import transact
from datetime import datetime

from celery.backends.base import BaseDictBackend
from celery.exceptions import TimeoutError

import AccessControl.User

from Products.Jobber.exceptions import NoSuchJobException
from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.celeryintegration import states
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

log = logging.getLogger("zen.celeryintegration")

CONNECTION_ENVIRONMENT = threading.local()


def _getContext(app):
    request = HTTPRequest(
        None,
        {
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8080',
            'REQUEST_METHOD': 'GET'
        },
        HTTPResponse(stdout=None)
    )
    return app.__of__(RequestContainer(REQUEST=request))


class ConnectionCloser(object):
    def __init__(self, connection):
        self.connection = connection

    def __del__(self):
        try:
            transaction.abort()
        except Exception:
            pass
        try:
            noSecurityManager()
            self.connection.close()
        except Exception:
            pass


class ZODBBackend(BaseDictBackend):
    """
    ZODB result backend for Celery.
    """
    CONN_MARKER = 'ZODBBackendConnection'
    _db = None

    def __init__(self, *args, **kwargs):
        super(ZODBBackend, self).__init__(*args, **kwargs)
        self._db_lock = threading.Lock()

    def get_db_options(self):
        options = getattr(self.app, 'db_options', None)
        if options is not None:
            return options.__dict__
        # This path should never be hit except in testing, because
        # Globals.DB will have been set before this method is even called.
        # Having this lets us have zendmd open a new db so we can test in
        # process, if we comment out getting the database from Globals in
        # db() below.
        from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
        return getGlobalConfiguration()

    @property
    def db(self):
        """
        Get a handle to the database by whatever means necessary
        """
        with self._db_lock:
            # Get the current database
            db = self._db
            if db is None:
                # Try to get the database off Globals (Zope, zendmd)
                db = getattr(Globals, 'DB', None)
                if db is None:
                    # Open a connection (CmdBase)
                    connectionFactory = getUtility(IZodbFactoryLookup).get()
                    options = self.get_db_options()
                    db, storage = connectionFactory.getConnection(**options)
                self._db = db
            return db

    @property
    def dmd(self):
        """
        Use a well-known connection to get a reliable dmd object.
        """
        closer = getattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER, None)

        if closer is None:
            conn = self.db.open()
            setattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER,
                    ConnectionCloser(conn))
            newSecurityManager(None, AccessControl.User.system)
            app = conn.root()['Application']
            # Configure zProperty descriptors
            setDescriptors(app.zport.dmd)
        else:
            app = closer.connection.root()['Application']

        return _getContext(app).zport.dmd

    @property
    def jobmgr(self):
        return self.dmd.JobManager

    def update(self, task_id, **properties):
        """
        Store properties on a JobRecord.
        """
        def _update():
            """
            Give the database time to sync incase a job record update
            was received before the job was created
            """

            @transact
            def _doupdate():
                self.jobmgr.update(task_id, **properties)

            try:
                for i in range(5):
                    try:
                        log.debug("Updating job %s - Pass %d", task_id, i+1)
                        _doupdate()
                        log.debug("Job %s updated", task_id)
                        break
                    except NoSuchJobException:
                        log.debug(
                            "Unable to find Job %s, retrying \n%s",
                            task_id, traceback.format_exc()
                        )
                        # Race condition. Wait.
                        time.sleep(0.25)
                        self.jobmgr._p_jar.sync()
                else:
                    # only runs if the for loop completes without breaking
                    log.warn(
                        "Job not updated.  Unable to save properties "
                        "%s to job %s", properties, task_id
                    )
            finally:
                self.reset()

        log.debug("Updating job %s with %s", task_id, properties)
        t = threading.Thread(target=_update)
        t.start()
        t.join()

# ----- BaseDictBackend Overrides -----------------------------------------

    def _store_result(self, task_id, result, status, traceback=None):
        """
        Store return value and status of an executed task.

        This runs in a separate thread with a short-lived connection, thereby
        guaranteeing isolation from the current transaction.
        """
        log.debug("[_store_result] %s %s %s", task_id, result, status)
        self.update(task_id, result=result, status=status,
                    date_done=datetime.utcnow(), traceback=traceback)
        return result

    def _get_task_meta_for(self, task_id):
        """
        Get task metadata for a task by id.
        """
        return self.jobmgr.getJob(task_id)

    def wait_for(self, task_id, timeout=None, propagate=True, interval=0.5):
        """
        Check status of a task and return its result when complete.

        This runs in a separate thread with a short-lived connection, thereby
        guaranteeing isolation from the current transaction.
        """
        status = self.get_status(task_id)
        if status in states.READY_STATES:
            # Job's already done, no need to spin up a thread.
            result = self.get_result(task_id)
        else:
            result_queue = Queue.Queue()

            def do_wait():
                try:
                    time_elapsed = 0.0
                    while True:
                        self.jobmgr._p_jar.sync()
                        status = self.get_status(task_id)
                        if status in states.READY_STATES:
                            result = self.get_result(task_id)
                            result_queue.put((status, result))
                            return
                        # avoid hammering the CPU checking status.
                        time.sleep(interval)
                        time_elapsed += interval
                        if timeout and time_elapsed >= timeout:
                            raise TimeoutError("The operation timed out.")
                finally:
                    self.reset()

            t = threading.Thread(target=do_wait)
            t.start()
            t.join()
            try:
                status, result = result_queue.get_nowait()
            except Queue.Empty:
                return

        if status in states.PROPAGATE_STATES and propagate:
            raise result
        else:
            return result

    def _forget(self, task_id):
        """
        Forget about a result.
        """
        # TODO: implement
        raise NotImplementedError("ZODBBackend does not support forget")

    def cleanup(self):
        """
        Delete expired metadata.
        """
        # TODO: implement
        raise NotImplementedError("ZODBBackend does not support cleanup")

    def reset(self):
        try:
            delattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER)
        except AttributeError:
            pass

    def process_cleanup(self):
        self._db = None
        self.reset()
