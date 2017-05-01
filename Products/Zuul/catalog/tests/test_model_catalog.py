import unittest
import transaction
import random

from Products.Zuul.tests.base import BaseTestCase, init_modelcatalog
from Products.Zuul.catalog.model_catalog import ModelCatalogClient
from Products.Zuul.catalog.interfaces import IModelCatalog
from Products.ZenModel.Device import Device
from Products.ZenModel.ZDeviceLoader import JobDeviceLoader
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from zenoss.modelindex.model_index import SearchParams
from zope.component import getUtility

dmd = ZenScriptBase(connect=True).dmd
device_classes = dmd.Devices.getPeerDeviceClassNames()
device_prefix = '/'.join(dmd.Devices.getPrimaryPath())

def generate_random_ip():
    return ".".join([str(random.randrange(0, 255, 1)) for x in range(4)])

def get_random_device_class():
    return device_prefix + random.choice(device_classes)

def load_random_device():
    ip = generate_random_ip()
    device_class = get_random_device_class()
    device_class = device_class[len("/zport/dmd/Devices"):]
    # load_device raises the IndexingEvent, which triggers catalog_object on the
    # ModelCatalogClient for the zope thread, but does not commit the transaction
    device = JobDeviceLoader(dmd).load_device(ip, device_class, 'none', 'localhost', manageIp=ip)
    return device

class ModelCatalogTest(BaseTestCase):

    def test_modelCatalogItemsFoundPostTransaction(self):
        """Tests that an item that is added to the index can be found after
        a commit occurs on the transaction.

        Also tests and item can be removed from catalog in a 'normal' scenario.
        """
        client = getUtility(IModelCatalog).get_client(dmd)
        # add the device
        dev = load_random_device()
        transaction.commit()
        # find it by id
        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        self.assertTrue(dev_res.id == dev.id, "Bad ID returned.  Expected {0}, got {1}.".format(dev.id, dev_res.id))
        # tx_state 0 means the two phase commit was completed normally
        self.assertTrue(dev_res.tx_state == 0, "Bad tx_state returned.  Expected 0, got {0}.".format(dev_res.tx_state))

        client.uncatalog_object(dev_res)
        transaction.commit()

        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))

    def test_modelCatalogItemsFoundMidTransactionSearch(self):
        """Tests that an item that is added to the index can be found
        before a commit occurs on the transaction, when commit_dirty is True.

        Also tests that after a mid-transaction search, followed by a commit,
        the mid-transaction item is deleted and the normal (post-commit) item
        has the correct tx_state.

        Also tests that the item can then be removed from the catalog.
        """
        client = getUtility(IModelCatalog).get_client(dmd)
        # add the device
        dev = load_random_device()
        # search for it before commiting, check the current transaction with commit_dirty True
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=True)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        self.assertTrue(dev_res.id == dev.id, "Bad ID returned.  Expected {0}, got {1}.".format(dev.id, dev_res.id))
        # tx_state tid means a search occurred mid-transaction
        self.assertTrue(dev_res.tx_state == client._data_manager._get_tid(),
        "Bad tx_state, expected {0}, got {1}.".format(client._data_manager._get_tid(), dev_res.tx_state))

        transaction.commit()
        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        self.assertTrue(dev_res.id == dev.id, "Bad ID returned.  Expected {0}, got {1}.".format(dev.id, dev_res.id))
        # tx_state 0 means the two phase commit was completed normally
        self.assertTrue(dev_res.tx_state == 0, "Bad tx_state returned.  Expected 0, got {0}.".format(dev_res.tx_state))

        client.uncatalog_object(dev_res)
        transaction.commit()

        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))

    def test_modelCatalogItemsNotFoundMidTransactionSearch(self):
        """Tests that an item that is added to the index can not be found
        before a commit occurs on the transaction, when commit_dirty is False.
        """
        client = getUtility(IModelCatalog).get_client(dmd)
        # add the device
        dev = load_random_device()
        # search for it before commiting, do not check the current transaction
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=False)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))

        transaction.abort()

        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))

    def test_modelCatalogItemsClearedMidTransactionSearch(self):
        """Tests that an item that is added to the index can be found
        before a commit occurs on the transaction, when commit_dirty is True, then,
        that item will still be found in a subsequent search when commit_dirty is False.

        Also tests that the item can then be removed from the catalog.
        """
        client = getUtility(IModelCatalog).get_client(dmd)
        # add the device
        dev = load_random_device()
        # search for it before commiting, check the current transaction with commit_dirty True
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=True)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        self.assertTrue(dev_res.id == dev.id, "Bad ID returned.  Expected {0}, got {1}.".format(dev.id, dev_res.id))
        # tx_state tid means a search occurred mid-transaction
        self.assertTrue(dev_res.tx_state == client._data_manager._get_tid(),
        "Bad tx_state, expected {0}, got {1}.".format(client._data_manager._get_tid(), dev_res.tx_state))

        # we did a dirty commit last time, so our item should still be there
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=False)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        # commit to test that we can uncatalog it
        transaction.commit()

        client.uncatalog_object(dev_res)
        transaction.commit()

        results = client.search(SearchParams({"id":dev.id}), dmd)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))

    def test_modelCatalogItemsFoundMidTransactionSearchAborted(self):
        """Tests that an item that is added to the index can be found
        before a commit occurs on the transaction.
        Also tests that after a mid-transaction search, followed by an abort,
        the mid-transaction item is deleted.
        """
        client = getUtility(IModelCatalog).get_client(dmd)
        dev = load_random_device()
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=True)
        self.assertTrue(results.total == 1, "Bad query results.  Expected 1 result, got {0}.".format(results.total))
        dev_res = next(results.results)
        self.assertTrue(dev_res.id == dev.id, "Bad ID returned.  Expected {0}, got {1}.".format(dev.id, dev_res.id))
        # tx_state tid means a search occurred during the two phase commit
        self.assertTrue(dev_res.tx_state == client._data_manager._get_tid(),
        "Bad tx_state, expected {0}, got {1}.".format(client._data_manager._get_tid(), dev_res.tx_state))

        transaction.abort()
        # verify that our mid-transaction device is discarded
        results = client.search(SearchParams({"id":dev.id}), dmd, commit_dirty=True)
        self.assertTrue(results.total == 0, "Bad query results.  Expected 0, got {0}".format(results.total))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ModelCatalogTest),))

if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
