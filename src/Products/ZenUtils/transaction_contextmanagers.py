##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from contextlib import contextmanager

import transaction


log = logging.getLogger("zenutils.txcontextmanager")

# define exception type to catch cases where current transaction is explicitly
# committed or aborted with in the body of the with statement (only necessary
# on abort)
class InvalidTransactionError(Exception):
    pass


@contextmanager
def zodb_transaction():
    try:
        txn = transaction.get()
        yield txn
    except Exception:
        if txn is not transaction.get():
            raise InvalidTransactionError(
                "could not abort transaction, was already aborted/committed "
                "within 'with' body"
            )
        try:
            txn.abort()
        except Exception:
            log.exception("failed to abort transaction")
        raise
    else:
        if txn is transaction.get():
            try:
                txn.commit()
            except Exception:
                log.exception("failed to commit transaction")


@contextmanager
def nested_transaction(xaDataManager=None):
    try:
        txn = transaction.get()
        sp = txn.savepoint()
        if xaDataManager is not None:
            txn.join(xaDataManager)
        yield
    except Exception:
        sp.rollback()
        if xaDataManager is not None:
            xaDataManager.abort(txn)
        raise
    else:
        pass
