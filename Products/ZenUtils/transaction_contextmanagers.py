##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

# context managers for transaction and state commit/rollback
from contextlib import contextmanager

import transaction

# define exception type to catch cases where current transaction is explicitly
# committed or aborted with in the body of the with statement (only necessary on
# abort)
class InvalidTransactionError(Exception): pass

@contextmanager
def zodb_transaction():
    try:
        txn = transaction.get()
        yield txn
    except:
        if txn is not transaction.get():
            raise InvalidTransactionError(
                "could not abort transaction, was already aborted/committed within 'with' body")
        try:
            txn.abort()
        # catch any internal exceptions that happen during abort
        except Exception:
            pass
        raise
    else:
        try:
            if txn is transaction.get():
                txn.commit()
        # catch any internal exceptions that happen during commit
        except Exception:
            pass

@contextmanager
def nested_transaction(xaDataManager=None):
    try:
        txn = transaction.get()
        sp = txn.savepoint()
        if xaDataManager is not None:
            txn.join(xaDataManager)
        yield
    except:
        try:
            sp.rollback()
            if xaDataManager is not None:
                xaDataManager.abort(txn)
        except:
            pass
        raise
    else:
        pass


