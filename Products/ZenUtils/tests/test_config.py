###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
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
from Products.ZenUtils.GlobalConfig import GlobalConfig
from Products.ZenUtils.config import ConfigLoader, ConfigError, Config
from StringIO import StringIO
from json import dumps as json

class ConfigTest(BaseTestCase):
    def test_ConfigLoader(self):
        config_file = StringIO(
            '# comment\n'
            '\n'
            'key1 value1\n'
            'key2 value2\n'
        )

        loader = ConfigLoader([config_file])
        options = loader()
        assert isinstance(options, Config), "Value is not a Config"
        assert options.key1 == 'value1'
        assert options.key2 == 'value2'

    def test_globalConfigLoader(self):
        config_file = StringIO(
            '# comment\n'
            '\n'
            'key1 value1\n'
            'key2 value2\n'
        )

        loader = ConfigLoader([config_file], config=GlobalConfig)
        options = loader()
        assert isinstance(options, GlobalConfig), "Value is not a GlobalConfig"
        assert options.key1 == 'value1'
        assert options.key2 == 'value2'

    def test_configUpdate(self):
        values = {
            'key1' : 'value1',
            'key2' : 'value2',
        }

        options = Config()
        options.update(values)

        assert options.key1 == 'value1'
        assert options.key2 == 'value2'

    def test_configInvalid(self):
        config_file = StringIO('key1\n')

        loader = ConfigLoader(config_file)

        self.assertRaises(ConfigError, loader)

        config_file = StringIO('key1_value\n')

        loader = ConfigLoader(config_file)

        self.assertRaises(ConfigError, loader)

        config_file = StringIO('1key value\n')

        loader = ConfigLoader(config_file)

        self.assertRaises(ConfigError, loader)

        config_file = StringIO('key&^$# value\n')

        loader = ConfigLoader(config_file)

        self.assertRaises(ConfigError, loader)

    def test_get(self):
        config_file = StringIO(
            '# comment\n'
            '\n'
            'key1 value1\n'
            'key2 value2\n'
            'intval 1\n'
            'floatval 10.23232\n'
            'boolval 1\n'
            'BOOL TRUE\n'
            'true true\n'
            'yes yes\n'
            'y y\n'
            'nboolval 0\n'
            'no no\n'
            'false false\n'
            'n n\n'
        )

        loader = ConfigLoader([config_file])
        options = loader()

        assert options.key1 == 'value1'
        assert options.key2 == 'value2'

        assert options['key1'] == 'value1'
        assert options['key2'] == 'value2'

        assert options.get('key1') == 'value1'
        assert options.get('key2') == 'value2'

        assert options.get('key3', None) is None

        assert options.intval == '1'
        assert options.getint('intval') == 1
        assert options.getint('floatval') is None
        assert options.getint('key1') is None
        assert options.getint('not a key') is None

        assert options.floatval == '10.23232'
        assert options.getfloat('floatval') == 10.23232

        assert options.BOOL == 'TRUE'
        assert options.getbool('BOOL') == True
        assert options.getbool('boolval') == True
        assert options.getbool('true') == True
        assert options.getbool('yes') == True
        assert options.getbool('y') == True

        assert options.nboolval == '0'
        assert options.getbool('nboolval') == False
        assert options.getbool('no') == False
        assert options.getbool('false') == False
        assert options.getbool('n') == False

    def test_json(self):
        config_file = StringIO(
            '# comment\n'
            '\n'
            'key1 value1\n'
        )

        loader = ConfigLoader([config_file])
        options = loader()
        assert json(options) == '{"key1": "value1"}'

def test_suite():
    return unittest.makeSuite(ConfigTest)