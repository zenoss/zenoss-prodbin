###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import sys
from optparse import OptionValueError, BadOptionError

from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.config import Config, ConfigLoader

CONFIG_FILE = zenPath('etc', 'global.conf')

class GlobalConfig(Config):
    """
    A method for retrieving the global configuration options
    outside of a daemon. This is used to configure the
    AMQP connection in Zope and zenhub

    @todo Add validation for expected keys and values
    """
    pass

_GLOBAL_CONFIG = ConfigLoader(CONFIG_FILE, GlobalConfig)
def getGlobalConfiguration():
    return _GLOBAL_CONFIG()


class _GlobalConfParserAdapter(object):
    def __init__(self, parser):
        self.parser = parser

    def apply(self):
        self.parser.defaults = self._getGlobalConfigFileDefaults()
        return self.parser

    def _getParametersFromConfig(self, lines):
        args = []
        validkeys = self.parser.get_default_values().__dict__.keys()

        for line in lines:
            if line.get('type', None) == 'option' and line['key'] in validkeys:
                args += ['--%s' % line['key'], line['value']]

        return args

    def _getGlobalConfigFileDefaults(self):
        """
        Parse a config file which has key-value pairs delimited by white space,
        and update the parser's option defaults with these values.
        """
        options = self.parser.get_default_values()
        lines = self._loadConfigFile(CONFIG_FILE)
        if lines:
            args = self._getParametersFromConfig(lines)
            try:
                self.parser._process_args([], args, options)
            except (BadOptionError, OptionValueError) as err:
                # Ignore it, we only care about our own options as defined in the parser
                pass
        return options.__dict__

    def _loadConfigFile(self, filename):
        """
        Parse a config file which has key-value pairs delimited by white space.

        @parameter filename: path to the configuration file
        @type filename: string
        """
        lines = []
        try:
            with open(filename) as file:
                for line in file:
                    if line.lstrip().startswith('#') or line.strip() == '':
                        lines.append(dict(type='comment', line=line))
                    else:
                        try:
                            key, value = line.strip().split(None, 1)
                        except ValueError:
                            lines.append(dict(type='option', line=line, key=line.strip(), value=None, option=None))
                        else:
                            option = self.parser.get_option('--%s' % key)
                            lines.append(dict(type='option', line=line, key=key, value=value, option=option))
        except IOError as e:
            errorMessage = 'WARN: unable to read config file {filename} \
                -- skipping. ({exceptionName}: {exception})'.format(
                filename=filename,
                exceptionName=e.__class__.__name__,
                exception=e
            )
            print >>sys.stderr, errorMessage
            return []

        return lines


def applyGlobalConfToParser(parser):
    return _GlobalConfParserAdapter(parser).apply()
