###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

import Pyro.core

from ZenEvents.EventManager import EventManager

class ZMServer(Pyro.core.ObjBase, EventManager):
    def __init__(self):
        Pyro.core.ObjBase.__init__(self)
        EventManager.__init__(self)

        
Pyro.core.initServer()
daemon=Pyro.core.Daemon()
uri=daemon.connect(ZMServer(),"ZMServer")
print "The daemon runs on port:",daemon.port
print "The object's uri is:",uri
daemon.requestLoop()
