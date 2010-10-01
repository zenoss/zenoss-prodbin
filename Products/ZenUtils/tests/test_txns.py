###########################################################################
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
'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/test_txns.py
'''
import unittest
from zope.interface import implements

from Products.ZenUtils.tests.orm import ORMTestCase
from Products.ZenUtils.orm import session, init_model, nested_transaction
from Products.ZenUtils.orm.ASMQDataManager import ASMQDataManager
from Products.ZenChain.guids import Guid
import random
import os
import string
import subprocess
import transaction

from asmqTestDefns import Publisher

import logging
log = logging.getLogger("ZenUtils.tests.txns")

log.setLevel(logging.DEBUG)


# faux guid generator
randomStr = lambda n=8 : ''.join(random.choice(string.ascii_letters+"0123456789") for i in xrange(n))
generateGuid = lambda : "TEST" + randomStr(32)
new_state = lambda : random.choice("RED ORANGE YELLOW GREEN BLUE PURPLE".split())

# context managers for transaction and state commit/rollback
from contextlib import contextmanager

# define test-specific exception, so as not to accidentally mask real exceptions
class TestTxnsException(Exception): pass

@contextmanager
def revertAttributeOnError(obj, attrname):
    prev_value = getattr(obj, attrname)
    try:
        yield
    except:
        log.debug( "restore %s to previous value %r" % (attrname, prev_value) )
        setattr(obj, attrname, prev_value)
        raise

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
        log.debug( "aborting uber-transaction")
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
        log.debug( "commiting uber-transaction")
        try:
            if txn is transaction.get():
                txn.commit()
        # catch any internal exceptions that happen during commit
        except Exception:
            pass

@contextmanager
def msg_publish(chan):
    try:
        log.debug( "enable tx channel methods for channel 0x%08x" % id(chan))
        chan.tx_select()
        yield
    except:
        log.debug( "cancel sending messages for channel 0x%08x" % id(chan))
        chan.tx_rollback()
        raise
    else:
        log.debug( "publish all messages for channel 0x%08x, and close channel" % id(chan))
        chan.tx_commit()
        chan.close()


class TestTransactions(ORMTestCase):
    _tables = (Guid,)

    def setUp(self):
        super(TestTransactions, self).setUp()
        self.connected = False

        try:
            # connect to events database
            init_model()

            self.pub = Publisher()
            self.connected = True

            # start up message listener and wait for it to report "ready"
            localpath = os.path.dirname(__file__)
            listener_script = os.path.join(localpath, "listen_db_messages.py")
            listener = subprocess.Popen(["python",listener_script], bufsize=1, shell=False, stdout=subprocess.PIPE)
            listener.stdout.readline()
            self.listener = listener
        except Exception:
            log.warning( "failed to setup amqp connection" )

    def tearDown(self):
        super(TestTransactions,self).tearDown()

        if not self.connected:
            log.debug( "skipping tearDown")
            return

        # shut down listener subprocess
        with msg_publish(self.pub.channel):
            self.pub.publish("FIN")


    def template_test_transaction_fn(self, n=10, raise_exception=False, raise_internal_only=False):
        global session

        if not self.connected:
            log.debug("skipping current test, no connection")
            return

        # get current count of guids in the database
        tally = session.query(Guid).count()
        self.state = "VIOLET"
        with msg_publish(self.pub.channel):
            log.debug("set listener record count (%d) %r" % (tally, self.pub.channel))
            self.pub.publish("INIT", str(tally))
            self.pub.publish("STATE", self.state)

        last_tally = tally
        self.added_recs = 0

        # start a transaction, update some guids, and send corresponding messages
        try:
            with zodb_transaction() as txn:
                if raise_internal_only:
                    # store records and send messages outside of nested txn
                    with nested_transaction() as session:
                        session.add_all(Guid(guid=generateGuid()) for i in xrange(n))

                    with msg_publish(self.pub.channel):
                        msg = self.pub.publish("ADDRECS",str(n))
                        self.state = new_state()
                        log.debug("state changed to " + self.state)
                        msg = self.pub.publish("STATE", self.state)
                        self.added_recs += n

                try:
                    with revertAttributeOnError(self, "state"):
                        with revertAttributeOnError(self, "added_recs"):
                            with nested_transaction(ASMQDataManager(self.pub.channel)) as session:
                                session.add_all(Guid(guid=generateGuid()) for i in xrange(n))
                                msg = self.pub.publish("ADDRECS",str(n))
                                self.added_recs += n
                                self.state = new_state()
                                log.debug("state changed to " + self.state)
                                msg = self.pub.publish("STATE", self.state)
                                if raise_exception:
                                    raise TestTxnsException("undo db and messages")
                except TestTxnsException:
                    if not raise_internal_only:
                        raise
        except TestTxnsException:
            pass

        with msg_publish(self.pub.channel):
            msg = self.pub.publish("STATUS")

        # read status line from listener, compare with current tally and state
        listener_status = self.listener.stdout.readline()

        # now get actual record count from database
        tally = session.query(Guid).count()

        expected_tally = last_tally + self.added_recs
        log.debug( "Expected/actual tally: %d/%d %s" % (expected_tally, tally, (("FAIL","OK")[expected_tally==tally])) )
        self.assertEqual(expected_tally, tally)

        expected_status = "%d %s\n" % (tally, self.state)
        log.debug( "Expected: " + expected_status.strip())
        log.debug( "Received: " + listener_status.strip() )
        self.assertEqual(expected_status, listener_status)


    def test_0transaction_commit(self):
        return self.template_test_transaction_fn()

    def test_1transaction_rollback(self):
        return self.template_test_transaction_fn(raise_exception=True)

    def test_2nested_transaction_rollback(self):
        return self.template_test_transaction_fn(raise_exception=True, raise_internal_only=True)



def test_suite():
    return unittest.makeSuite(TestTransactions)

