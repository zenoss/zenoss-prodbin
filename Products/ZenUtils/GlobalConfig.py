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