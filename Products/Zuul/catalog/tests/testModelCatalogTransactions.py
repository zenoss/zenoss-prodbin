##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import unittest

from Products.AdvancedQuery import Eq, MatchGlob
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import ModelCatalogDataManager, SearchParams, TX_SEPARATOR
from Products.Zuul.catalog.indexable import MODEL_INDEX_UID_FIELD as SOLR_UID
from Products.Zuul.catalog.indexable import OBJECT_UID_FIELD as UID

from zenoss.modelindex.model_index import SearchParams


class TestModelCatalogTransactions(BaseTestCase):

    def afterSetUp(self):
        super(TestModelCatalogTransactions, self).afterSetUp()
        # Lets change the ModelCatalogTestDataManager with ModelCatalogDataManager
        self.model_catalog = IModelCatalogTool(self.dmd)
        self.data_manager = ModelCatalogDataManager('localhost:8983')
        self.model_catalog.model_catalog_client._data_manager = self.data_manager
        # get a refence to model_index to be able to fo checks bypassing the data manager
        self.model_index = self.data_manager.model_index

    def beforeTearDown(self):
        # we dont need to put back the test data manager since each test creates its own
        pass

    def _get_transaction_state(self):
        tid = self.data_manager._get_tid()
        return self.data_manager._current_transactions.get(tid)

    def _check_tx_state(self, pending=None, temp_indexed=None, temp_deleted=None):
        tx_state = self._get_transaction_state()

        if pending and isinstance(pending, basestring):
            pending = [ pending ]
        if temp_indexed and isinstance(temp_indexed, basestring):
            temp_indexed = [ temp_indexed ]
        if temp_deleted and isinstance(temp_deleted, basestring):
            temp_deleted = [ temp_deleted ]

        if pending:
            for uid in pending:
                self.assertTrue(uid in tx_state.pending_updates)
        if temp_indexed:
            for uid in temp_indexed:
                self.assertTrue(uid in tx_state.temp_indexed_uids)
                self.assertFalse(uid in tx_state.temp_deleted_uids)
        if temp_deleted:
            for uid in temp_deleted:
                self.assertTrue(uid in tx_state.temp_deleted_uids)
                self.assertFalse(uid in tx_state.temp_indexed_uids)

    def _validate_temp_indexed_results(self, results, expected_object_uids):
        found_object_uids = set()
        for result in results:
            found_object_uids.add(getattr(result, UID))
            self.assertNotEquals(getattr(result, UID), getattr(result, SOLR_UID))
            self.assertTrue(getattr(result, UID) in getattr(result, SOLR_UID))
            self.assertTrue( TX_SEPARATOR in getattr(result, SOLR_UID) )
        self.assertEquals(set(found_object_uids), set(expected_object_uids))

    def testDataManager(self):
        tx_state = self._get_transaction_state()
        # before any changes are made, tx_state is None
        self.assertIsNone(tx_state)
        device_class_1 = "device_class_1"
        device_class_2 = "device_class_2"

        # create an organizer
        dc_1 = self.dmd.Devices.createOrganizer(device_class_1)
        tx_state = self._get_transaction_state()
        dc_1_uid = dc_1.idx_uid()

        # Some tx_state checks
        self.assertIsNotNone(tx_state)
        self.assertTrue( len(tx_state.pending_updates) == 1 )
        self.assertTrue( len(tx_state.indexed_updates) == 0 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 0 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 0 )

        # The new organizer index update should have been buffered in tx_state
        self._check_tx_state(pending=dc_1_uid)

        # A search with commit_dirty=False should not find the new device organizer
        search_results = self.model_catalog.search(query=Eq(UID, dc_1_uid), commit_dirty=False)
        self.assertEquals(len(search_results), 0)

        # A search with commit_dirty=True must find the new device organizer
        search_results = self.model_catalog.search(query=Eq(UID, dc_1_uid), commit_dirty=True)
        # model catalog should return the dirty doc
        self.assertEquals(len(search_results), 1)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid])

        # the tx_state object should have been updated appropiately
        self._check_tx_state(temp_indexed=dc_1_uid)
        self.assertTrue( len(tx_state.pending_updates) == 0 )
        
        # create another organizer
        dc_2 = self.dmd.Devices.createOrganizer(device_class_2)
        dc_2_uid = dc_2.idx_uid()

        # check tx_state has been updated accordinly
        self._check_tx_state(pending=dc_2_uid, temp_indexed=dc_1_uid)

        # search for both device classes with commit_dirty=False, it should only return dc_1_uid
        query = MatchGlob(UID, "/zport/dmd/Devices/device_class*")
        search_results = self.model_catalog.search(query=query, commit_dirty=False)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid])
        # tx_state should not have changed
        self._check_tx_state(pending=dc_2_uid, temp_indexed=dc_1_uid)

        # now with commit_dirty=True
        search_results = self.model_catalog.search(query=query, commit_dirty=True)
        self._check_tx_state(temp_indexed=[dc_1_uid, dc_2_uid])
        # it should return 2 device classes
        self.assertEquals(len(search_results), 2)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_1_uid, dc_2_uid])

        # Lets delete device_class_2
        self.dmd.Devices._delObject(device_class_1)
        self._check_tx_state(pending=[dc_1_uid])
        # a search with commit = True should not return device_class_1 anymore
        search_results = self.model_catalog.search(query=query, commit_dirty=True)
        self._validate_temp_indexed_results(search_results, expected_object_uids=[dc_2_uid])
        self._check_tx_state(temp_deleted=[dc_1_uid])

        tx_state = self._get_transaction_state()
        self.assertTrue( len(tx_state.pending_updates) == 0 )
        self.assertTrue( len(tx_state.indexed_updates) == 2 )
        self.assertTrue( len(tx_state.temp_indexed_uids) == 1 )
        self.assertTrue( len(tx_state.temp_deleted_uids) == 1 )

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestModelCatalogTransactions),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
