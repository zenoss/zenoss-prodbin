##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import mock
import unittest

from Products.DataCollector.PythonClient import PythonClient


class TestPythonClient(unittest.TestCase):
    def test_getResults_order(self):
        """PythonClient.getResults() should return orderly results.

        Specifically what this means is that regardless of which data it's able
        to get first, it will return the plugin results in the order in which
        the plugins are configured. This is sometimes required when modeler
        plugins implicitely depend on each other.

        """
        plugins = [mock.Mock(), mock.Mock()]

        client = PythonClient(mock.Mock(), mock.Mock(), plugins)
        client.collectComplete('FIRST', plugins[0])
        client.collectComplete('LAST', plugins[-1])
        self.assertEquals(
            client.getResults(),
            [(plugins[0], 'FIRST'), (plugins[-1], 'LAST')],
            "plugins processed in order, but getResults() was out of order")

        client = PythonClient(mock.Mock(), mock.Mock(), plugins)
        client.collectComplete('LAST', plugins[-1])
        client.collectComplete('FIRST', plugins[0])
        self.assertEquals(
            client.getResults(),
            [(plugins[0], 'FIRST'), (plugins[-1], 'LAST')],
            "plugins processed out of order, and getResults() was out of order")
