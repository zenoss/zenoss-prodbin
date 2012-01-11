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

def installReactor():
    # Tries to install epoll first, then poll, and if neither are
    # available, the default select reactor will install when
    # twisted.internet.reactor is imported.
    try:
        from select import epoll
        from twisted.internet import epollreactor
        epollreactor.install()
    except ImportError:
        try:
            from select import poll
            from twisted.internet import pollreactor
            pollreactor.install()
        except ImportError:
            pass


import sys
if 'zope.testing' in sys.modules.keys():
    from twisted.python.runtime import platform
    platform.supportsThreads = lambda : None

