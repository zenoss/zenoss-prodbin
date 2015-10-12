##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from Products.ZenModel.ZenPack import ZenPack


class TestZenPack(unittest.TestCase):

    def test_getZProperties(self):
        class ZenPack1(ZenPack):
            pass

        self.assertEquals(ZenPack1.getZProperties(), {})

        class ZenPack2(ZenPack):
            packZProperties = [
                ('zMyString', 'default', 'string'),
                ]

        self.assertEquals(ZenPack2.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                },
            })

        class ZenPack3(ZenPack):
            packZProperties_data = {
                'zMyString': {
                    'type': 'string',
                    'defaultValue': 'default',
                    'category': 'My Category',
                    'label': 'My String',
                    'description': 'This is my string.',
                    },
                'zMyNoType': {
                    'defaultValue': 'default',
                    'description': "I don't have a type.",
                    },
                'zMyNoDefault': {
                    'type': 'string',
                    'description': "I don't have a default value.",
                    },
                }

        self.assertEquals(ZenPack3.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                'category': 'My Category',
                'label': 'My String',
                'description': 'This is my string.',
                },
            })

        class ZenPack4(ZenPack):
            packZProperties = [
                ('zMyString', 'default', 'string'),
                ('zMyLines', ['default'], 'lines'),
                ]

            packZProperties_data = {
                'zMyString': {
                    'type': 'int',
                    'defaultValue': 'new-default',
                    'category': 'Mine',
                    'label': 'My String',
                    'description': 'This is my string.',
                    },
                'zMyBoolean': {
                    'type': 'boolean',
                    'defaultValue': True,
                    'category': 'Mine',
                    'label': 'My Boolean',
                    'description': 'This is my boolean.',
                    },
                }

        self.assertEquals(ZenPack4.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                'category': 'Mine',
                'label': 'My String',
                'description': 'This is my string.',
                },
            'zMyLines': {
                'type': 'lines',
                'defaultValue': ['default'],
                },
            'zMyBoolean': {
                'type': 'boolean',
                'defaultValue': True,
                'category': 'Mine',
                'label': 'My Boolean',
                'description': 'This is my boolean.',
                },
            })
