#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
from sqlalchemy import create_engine
import meta
import transaction
from zope.sqlalchemy.datamanager import join_transaction
from zope.sqlalchemy import ZopeTransactionExtension

session = meta.Session

import logging
log = logging.getLogger('zen.ORM')

model_ready = False
def init_model(user="zenoss", passwd="zenoss", host="localhost", port="3306",
               db="events"):
    """
    Call at startup.
    """
    global model_ready
    if not model_ready:
        meta.engine = create_engine(
            ('mysql://%(user)s:%(passwd)s@%(host)s:%(port)s'
             '/%(db)s?charset=utf8') % locals(),
            pool_recycle=60)
        meta.metadata.bind = meta.engine
        meta.Session.configure(autoflush=False, autocommit=False, binds={
            meta.metadata:meta.engine}, 
            twophase=True, 
            extension=ZopeTransactionExtension()
        )
        model_ready = True


class nested_transaction(object):
    """
    Context manager for managing commit and rollback on error. Example usage:

    with nested_transaction() as session:
        ob = ModelItem()
        session.add_all([ob])

    # optional
    with nested_transaction(xadatamgr) as session:
        # XA data manager will be joined with the zope and SQLAlchemy
        # transactions, so that all commit or rollback together
        etc.

    It'll be committed for you and rolled back if there's a problem.
    """
    def __init__(self, xaDataManager=None):
        self.session = session()
        self.session.expire_on_commit = True
        self.session.autocommit = False
        self.savepoint = transaction.savepoint()

        if xaDataManager is not None:
            log.debug("nested_transaction.__init__: enabling two-phase commit")
            self.session.twophase = True
            join_transaction(self.session)
            transaction.get().join(xaDataManager)
        else:
            log.debug("nested_transaction.__init__: local commit only")

    def __enter__(self):
        if self.session.is_active:
            self.session.begin_nested()
        else:
            self.session.begin(subtransactions=True)
        return self.session

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                log.debug('nested_transaction.__exit__: Committing nested transaction')
                if not self.session.twophase:
                    self.session.commit()
            except Exception as e:
                log.exception(e)
                log.error('nested_transaction.__exit__: Rolling back after commit failure')
                self.savepoint.rollback()
                raise
        else:
            # Error occurred
            log.exception(value)
            log.debug('nested_transaction.__exit__: Rolling back')
            self.savepoint.rollback()

