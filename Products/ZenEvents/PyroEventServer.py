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

from threading import Timer

import Pyro.core

from ZenEvents.EventDatabase import EventDatabase

class ZEPyroServer(Pyro.core.ObjBase, EventDatabase):

    def __init__(self):
        Pyro.core.ObjBase.__init__(self)
        EventDatabase.__init__(self)

        
Pyro.core.initServer()
daemon=Pyro.core.Daemon()
uri=daemon.connect(ZEPyroServer(),"ZEServer")
print "The daemon runs on port:",daemon.port
print "The object's uri is:",uri
daemon.requestLoop()
