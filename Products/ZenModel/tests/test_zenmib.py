##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import mock
import os
from collections import namedtuple

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.zenmib import (
    DumpFileProcessor, MIBFileProcessor, SMIDump, SMIDumpTool
)
from Products.ZenUtils.mib import MIBFile


_dir = os.path.dirname(__file__)
_testmibdir = os.path.abspath(os.path.join(
    _dir, "..", "..", "ZenUtils", "mib", "tests"
))


def _readfile(path):
    with open(path, 'r') as fd:
        return fd.read()


class TestMIBFileProcessor(BaseTestCase):

    def _checkResults(self):
        module = self.dmd.unrestrictedTraverse(
            "/zport/dmd/Mibs/mibs/SMIDUMP01-MIB", None
        )
        self.assertTrue(module is not None)
        self.assertEqual(module.nodeCount(), 4)
        self.assertEqual(module.notificationCount(), 1)
        node_names = set([
            "dumpCount", "smidump01",
            "smidump01Notifications", "smidump01Objects"
        ])
        for node in module.nodes():
            if node.id in node_names:
                node_names.remove(node.id)
        self.assertEqual(len(node_names), 0)
        self.assertEqual(
            module.notifications()[0].id, "smidump01Notification01"
        )

    @mock.patch("Products.ZenModel.zenmib.SMIDumpTool", spec_set=SMIDumpTool)
    def test_MIBFileProcessor(self, mockSMIDumpTool):
        dump_filename = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib.py")
        dump_data = _readfile(dump_filename)
        dump = SMIDump(dump_data)

        mockTool = mock.Mock(spec=SMIDumpTool)
        mockTool.run = mock.Mock(return_value=dump)
        mockSMIDumpTool.return_value = mockTool

        source = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib")
        source_data = _readfile(source)
        expectedMIBFile = MIBFile(source, source_data)

        options = namedtuple(
            "options",
            "mibsdir mibdepsdir path keeppythoncode "
            "pythoncodedir downloaddir extractdir evalSavedPython"
        )
        options.mibsdir = "/opt/zenoss/share/mibs/site"
        options.mibdepsdir = "/opt/zenoss/share/mibs"
        options.path = ""
        options.keeppythoncode = False

        log = logging.getLogger("zen.testzenmib")
        log.setLevel(logging.DEBUG)
        log.manager.disable = 0  # re-enable log output

        processor = MIBFileProcessor(log, self.dmd, options, [source])
        processor.run()

        mockTool.run.assert_called_with(expectedMIBFile)
        self._checkResults()

    def test_DumpFileProcessor(self):
        dump_filename = os.path.join(_testmibdir, "SMIDUMP01-MIB.mib.py")
        # dump_data = _readfile(dump_filename)
        # dump = SMIDump(dump_data)

        options = namedtuple(
            "options",
            "mibsdir mibdepsdir path keeppythoncode "
            "pythoncodedir downloaddir extractdir evalSavedPython"
        )
        options.mibsdir = "/opt/zenoss/share/mibs/site"
        options.mibdepsdir = "/opt/zenoss/share/mibs"
        options.path = ""
        options.evalSavedPython = [dump_filename]
        options.keeppythoncode = False

        log = logging.getLogger("zen.testzenmib")
        # log.setLevel(logging.DEBUG)
        # log.manager.disable = 0  # re-enable log output

        processor = DumpFileProcessor(log, self.dmd, options, [dump_filename])
        processor.run()

        self._checkResults()
