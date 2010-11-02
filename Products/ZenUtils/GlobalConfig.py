###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenUtils.Utils import zenPath
CONFIG_FILE = zenPath('etc', 'global.conf')

class GlobalConfig(object):
    """
    A method for retrieving the global configuration options
    outside of a daemon. This is used to configure the
    AMQP connection in Zope and zenhub
    """
    def __init__(self):
        options = {}
        # read the global.conf
        with open(CONFIG_FILE, 'r') as fp:
            for line in fp.readlines():
                if line.lstrip().startswith('#') or line.strip() == '':
                    # comment
                    continue
                option, value = line.split(None, 1)
                options[option] = value.strip()

        def _createProperty(name):
            def getter(self):
                return getattr(self, '_' + name)
            return property(getter)

        # create a read only property for each option and value
        for option, value in options.iteritems():
            setattr(self, '_' + option, value)
            setattr(self.__class__, option, _createProperty(option))


_GLOBALCONFIG = None
def getGlobalConfiguration():
    global _GLOBALCONFIG
    if not _GLOBALCONFIG:
        _GLOBALCONFIG = GlobalConfig()
    return _GLOBALCONFIG
