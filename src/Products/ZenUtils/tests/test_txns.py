##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import unittest

import amqp
import mock
import transaction

from ..AmqpDataManager import AmqpDataManager
from ..transaction_contextmanagers import nested_transaction, zodb_transaction

log = logging.getLogger("ZenUtils.tests.txns")
log.setLevel(logging.DEBUG)


class TestAmqpDataManager(unittest.TestCase):
    def setUp(t):
        transaction.commit()
        t.channel = mock.Mock(spec=amqp.Channel)

    def tearDown(t):
        transaction.abort()
        del t.channel

    def test_init_without_transactionmanager(t):
        manager = AmqpDataManager(t.channel)
        t.assertIs(manager.channel, t.channel)
        t.assertIs(manager.transaction_manager, transaction.manager)
        t.channel.tx_select.assert_called_once_with()

    def test_init_with_transactionmanager(t):
        manager = AmqpDataManager(t.channel, transaction.manager.manager)
        t.assertIs(manager.channel, t.channel)
        t.assertIs(manager.transaction_manager, transaction.manager.manager)
        t.channel.tx_select.assert_called_once_with()

    def test_abort(t):
        t.channel.is_open = True
        manager = AmqpDataManager(t.channel)
        tx = transaction.get()
        tx.join(manager)
        transaction.abort()
        t.channel.tx_rollback.assert_called_once_with()
        t.channel.tx_commit.assert_not_called()

    def test_commit(t):
        t.channel.is_open = True
        manager = AmqpDataManager(t.channel)
        tx = transaction.get()
        tx.join(manager)
        transaction.commit()
        t.channel.tx_commit.assert_called_once_with()
        t.channel.tx_rollback.assert_not_called()

    def test_contextmgr(t):
        t.channel.is_open = True
        manager = AmqpDataManager(t.channel)
        with zodb_transaction() as tx:
            tx.join(manager)
        t.channel.tx_commit.assert_called_once_with()
        t.channel.tx_rollback.assert_not_called()

    def test_contextmgr_failure(t):
        t.channel.is_open = True
        manager = AmqpDataManager(t.channel)
        try:
            with zodb_transaction() as tx:
                tx.join(manager)
                raise RuntimeError("boom!")
        except RuntimeError:
            pass
        finally:
            t.channel.tx_rollback.assert_called_once_with()
            t.channel.tx_commit.assert_not_called()

    def test_nested(t):
        t.channel.is_open = True
        with nested_transaction(AmqpDataManager(t.channel)):
            pass
        transaction.commit()
        t.channel.tx_commit.assert_called_once_with()
        t.channel.tx_rollback.assert_not_called()

    def test_nested_failure(t):
        t.channel.is_open = True
        try:
            with nested_transaction(AmqpDataManager(t.channel)):
                raise RuntimeError("boom!")
        except RuntimeError:
            pass
        finally:
            t.channel.tx_rollback.assert_has_calls([mock.call(), mock.call()])
            t.channel.tx_commit.assert_not_called()
