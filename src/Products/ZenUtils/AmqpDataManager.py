##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys
import time
import logging

import transaction

from transaction.interfaces import IDataManager
from zope.interface import implementer

log = logging.getLogger("zen.amqpdatamanager")


# DataManager class for adding msg queueing to zope and other XA
# transaction cohorts.  Usage with nested_transaction:
#
#  with nested_transaction(AmqpDataManager(publisher.channel)) as txn:
#      # perform zope db commands
#      # perform SQLAlchemy db commands
#      publisher.publish(msg)
#


@implementer(IDataManager)
class AmqpDataManager(object):
    """Objects that manage transactional storage.

    These objects may manage data for other objects, or they may manage
    non-object storages, such as relational databases.  For example,
    a ZODB.Connection.

    Note that when some data is modified, that data's data manager should
    join a transaction so that data can be committed when the user commits
    the transaction.
    """

    def __init__(self, channel, txnmgr=None):
        self.channel = channel
        self.channel.tx_select()  # initializes transactional mode
        # Get an ITransactionManager instance
        mgr = txnmgr if txnmgr is not None else transaction.manager
        self.transaction_manager = mgr

    def abort(self, transaction):
        """Abort a transaction and forget all changes.

        Abort must be called outside of a two-phase commit.

        Abort is called by the transaction manager to abort transactions
        that are not yet in a two-phase commit.
        """
        # discard any messages that have been buffered
        log.debug("abort")
        if self.channel.is_open:
            self.channel.tx_rollback()

    def commit(self, transaction):
        """Commit modifications to registered objects.

        Save changes to be made persistent if the transaction commits (if
        tpc_finish is called later).  If tpc_abort is called later, changes
        must not persist.

        This includes conflict detection and handling.  If no conflicts or
        errors occur, the data manager should be prepared to make the
        changes persist when tpc_finish is called.
        """
        log.debug("commit")

    # Two-phase commit protocol.  These methods are called by the ITransaction
    # object associated with the transaction being committed.  The sequence
    # of calls normally follows this regular expression:
    #     tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(self, transaction):
        """Begin commit of a transaction, starting the two-phase commit.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        log.debug("tpc_begin")

    def tpc_finish(self, transaction):
        """Indicate confirmation that the transaction is done.

        Make all changes to objects modified by this transaction persist.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.  If this raises an exception, the
        database is not expected to maintain consistency; it's a
        serious error.
        """
        log.debug("tpc_finish")
        try:
            self.channel.tx_commit()
        except Exception:
            log.exception("tpc_finish completed FAIL")
        else:
            log.debug("tpc_finish completed OK")

    def tpc_vote(self, transaction):
        """Verify that a data manager can commit the transaction.

        This is the last chance for a data manager to vote 'no'.  A
        data manager votes 'no' by raising an exception.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        log.debug("tpc_vote")

    def tpc_abort(self, transaction):
        """Abort a transaction.

        This is called by a transaction manager to end a two-phase commit on
        the data manager.  Abandon all changes to objects modified by this
        transaction.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.
        """
        log.debug("tpc_abort")
        try:
            self.channel.tx_rollback()
        except Exception:
            log.exception("tpc_abort completed FAIL")
        else:
            log.debug("tpc_abort completed OK")

    def sortKey(self):
        """Return a key to use for ordering registered DataManagers."""
        # this data manager must always go last
        return "~~~~~~~"


#
# usage outside of zope transaction
#    with AmqpTransaction(publisher.channel) as txn:
#        publisher.publish(msg)
#        publisher.publish(msg2)
#
class AmqpTransaction(object):
    def __init__(self, channel):
        self.datamgr = AmqpDataManager(channel)
        self.txnid = int(time.clock() * 1e6) % sys.maxint

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                self.datamgr.tpc_begin(self.txnid)
                self.datamgr.commit(self.txnid)
                self.datamgr.tpc_vote(self.txnid)
                self.datamgr.tpc_finish(self.txnid)
            except Exception:
                self.datamgr.tpc_abort(self.txnid)
                raise
        else:
            try:
                self.datamgr.abort(self.txnid)
            except Exception:
                log.exception("failed to abort")
