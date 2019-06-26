#!/usr/bin/env python

from __future__ import absolute_import

import mock
import unittest

from . import common

_DATA = {"module": "Products.ZenModel.migrate.updateZenJobsForCelery31"}


class Test_UpdateZenJobsForCelery31(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test the UpdateZenJobsForCelery31 class."""

    initial_servicedef = 'zenoss-resmgr-6.3.2.json'
    expected_servicedef = 'zenoss-resmgr-6.3.2-updateZenJobsForCelery31.json'
    migration_module_name = 'updateZenJobsForCelery31'
    migration_class_name = 'UpdateZenJobsForCelery31'

    dmd = mock.Mock()

    def test_cutover_correctness(self, *args, **kwargs):
        with mock.patch(
            "{module}.manage_addJobManager".format(**_DATA), autospec=True,
        ):
            super(
                Test_UpdateZenJobsForCelery31, self,
            ).test_cutover_correctness(*args, **kwargs)

    def test_cutover_idempotence(self, *args, **kwargs):
        with mock.patch(
            "{module}.manage_addJobManager".format(**_DATA), autospec=True,
        ):
            super(
                Test_UpdateZenJobsForCelery31, self,
            ).test_cutover_idempotence(*args, **kwargs)


if __name__ == '__main__':
    unittest.main()
