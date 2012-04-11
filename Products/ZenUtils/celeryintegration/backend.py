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
import threading
import transaction
from zope.component import getUtility
from datetime import datetime
from celery.backends.base import BaseDictBackend
from celery import states
from ZODB.transact import transact
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
from persistent.dict import PersistentDict


CONNECTION_ENVIRONMENT = threading.local()


class ConnectionCloser(object):
    def __init__(self, connection):
        self.connection = connection

    def __del__(self):
        try:
            transaction.abort()
        except Exception:
            pass
        self.connection.close()


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
        self._db_lock.acquire()
        try:
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
        finally:
            self._db_lock.release()

    @property
    def dmd(self):
        """
        Use a well-known connection to get a reliable dmd object.
        """
        conn = None
        closer = getattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER, None)

        if closer is None:
            conn = self.db.open()
            setattr(CONNECTION_ENVIRONMENT, self.CONN_MARKER,
                    ConnectionCloser(conn))
        else:
            conn = closer.connection

        app = conn.root()['Application']
        return app.zport.dmd

    @property
    def jobmgr(self):
        return self.dmd.JobManager

    @transact
    def _store_result(self, task_id, result, status, traceback=None):
        """
        Store return value and status of an executed task.
        """
        self.jobmgr._p_jar.sync()
        meta = PersistentDict()
        meta.update({
            "id": task_id,
            "status": status,
            "result": result,
            "date_done": datetime.utcnow(),
            "traceback": traceback
        })
        self.jobmgr._setOb(task_id, meta)
        return result

    def _get_task_meta_for(self, task_id):
        """
        Get task metadata for a task by id.
        """
        self.jobmgr._p_jar.sync()
        d = {}
        try:
            d.update(self.jobmgr._getOb(task_id))
        except AttributeError:
            return {"status": states.PENDING, "result": None}
        return d

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


