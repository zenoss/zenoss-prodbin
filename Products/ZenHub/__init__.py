###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""Turn ZenHub into a module"""

XML_RPC_PORT = 8081
PB_PORT = 8789
ZENHUB_ZENRENDER = "zenhubrender"

import sys
if 'zope.testing' in sys.modules.keys():
    from twisted.python.runtime import platform
    platform.supportsThreads = lambda : None

