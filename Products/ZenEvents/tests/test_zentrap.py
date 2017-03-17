from Products.ZenTestCase.BaseTestCase import BaseTestCase
from mock import patch
from Products.ZenEvents.zentrap import TrapTask


class TrapTaskUnitTest(BaseTestCase):

    @patch("Products.ZenEvents.zentrap.TrapTask.__init__")
    def test_convert_value_snmp_object_id(self, mock_traptask_init):
        mock_traptask_init.return_value = None
        trap_task = TrapTask()

        value = (1, 2, 3, 4)
        self.assertEqual(
            trap_task._convert_value(value),
            "1.2.3.4"
        )

    @patch("Products.ZenEvents.zentrap.TrapTask.__init__")
    def test_convert_value_decodes_utf8(self, mock_traptask_init):
        mock_traptask_init.return_value = None
        trap_task = TrapTask()

        value = 'valid utf8 string \xc3\xa9'.encode('utf8')
        self.assertEqual(
            trap_task._convert_value(value),
            u'valid utf8 string \xe9'.decode('utf8')
        )

    '''
    @patch("Products.ZenEvents.zentrap.TrapTask.__init__")
    def test_convert_value_decodes_datetime(self, mock_traptask_init):
        mock_traptask_init.return_value = None
        trap_task = TrapTask()

        self.assertTrue(False, "implement test")
    '''

    @patch("Products.ZenEvents.zentrap.TrapTask.__init__")
    def test_convert_value_handles_invalid_chars(self, mock_traptask_init):
        mock_traptask_init.return_value = None
        trap_task = TrapTask()

        value = '\xde\xad\xbe\xef\xfe\xed\xfa\xce'
        self.assertEqual(
            trap_task._convert_value(value),
            'Failed to decode: converted to BASE64:"3q2+7/7t+s4="'
        )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TrapTaskUnitTest))
    return suite
