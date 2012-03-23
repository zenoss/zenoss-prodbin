###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.ZenBackup import strip_definer

class TestDefiner(BaseTestCase):
    """Test the DEFINER stripping."""

    def test50013(self):
        input_text = \
"""foo
/*!50013 DEFINER=`user_a`@`localhost` SQL SECURITY DEFINER */
bar"""
        expected = \
"""foo

bar"""
        actual = "\n".join(strip_definer(line) for line in input_text.splitlines())
        self.assertEqual(actual, expected)

    def test50017(self):
        input_text = \
"""/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`10.175.209.87`*/ /*!50003 TRIGGER `event_summary_index_queue_insert` AFTER INSERT ON `event_summary`
FOR EACH ROW BEGIN
INSERT INTO `event_summary_index_queue` SET uuid=NEW.uuid, update_time=NEW.update_time;
END */;;"""
        expected = \
"""/*!50003 CREATE*/  /*!50003 TRIGGER `event_summary_index_queue_insert` AFTER INSERT ON `event_summary`
FOR EACH ROW BEGIN
INSERT INTO `event_summary_index_queue` SET uuid=NEW.uuid, update_time=NEW.update_time;
END */;;"""
        actual = "\n".join(strip_definer(line) for line in input_text.splitlines())
        self.assertEqual(actual, expected)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestDefiner),))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
