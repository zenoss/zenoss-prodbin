###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals
import time
import threading
import Queue
import transaction
import logging
from zope.component import getUtility
from ZODB.POSException import ConflictError
from datetime import datetime
from celery.backends.base import BaseDictBackend
from celery.exceptions import TimeoutError
import AccessControl.User
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.ZenUtils.celeryintegration import states
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
from Products.Jobber.exceptions import NoSuchJobException
from Products.ZenRelations.ZenPropertyManager import setDescriptors
log = logging.getLogger("zen.celeryintegration")

CONNECTION_ENVIRONMENT = threading.local()


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
        BaseDictBackend.__init__(self, *args, **kwargs)
        self._db_lock = threading.Lock()

    def get_db_options(self):
        options = getattr(self.app, 'db_options', None)
        if options is not None:
            return options.__dict__
        else:
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
                # Try to get it off Globals (Zope, zendmd)
                db = getattr(Globals, 'DB', None)
                if db is None:
                    # Open a connection (CmdBase)
                    connectionFactory = getUtility(IZodbFactoryLookup).get()
                    db, storage = connectionFactory.getConnection(**self.get_db_options())
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

        return app.zport.dmd

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
            try:
                for i in range(5):
                    try:
                        self.jobmgr.update(task_id, **properties)
                        transaction.commit()
                        return
                    except (NoSuchJobException, ConflictError):
                        log.debug("Unable to find Job %s, retrying ", task_id)
                        # Race condition. Wait.
                        time.sleep(0.25)
                        self.dmd._p_jar.sync()

                log.warn("Unable to save properties  %s to job %s", properties, task_id)
            finally:
                self.reset()
        t = threading.Thread(target=_update)
        t.start()
        t.join()

    def _store_result(self, task_id, result, status, traceback=None):
        """
        Store return value and status of an executed task.

        This runs in a separate thread with a short-lived connection, thereby
        guaranteeing isolation from the current transaction.
        """
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
            # Already done, no need to spin up a thread to poll
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
                            result_queue.put((status, self.get_result(task_id)))
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
        self._db = None
        try:
            delattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER)
        except AttributeError:
            pass

    def process_cleanup(self):
        self.reset()
