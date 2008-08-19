###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate
import logging
log = logging.getLogger("zen.migrate")

class monitorAsHeartbeatDevice(Migrate.Step):
    """
    In version 2.3 we have changed the device component of heartbeat events to
    use the options.monitor value instead of socket.getfqdn(). This will result
    in heartbeat failures for all daemons upon upgrade to Zenoss 2.3.

    This script will automatically clear any heartbeats that aren't from a
    defined collector. This extra check makes it safe to re-run this migrate
    script on a 2.3+ instance without worrying about deleting heartbeats that
    shouldn't be deleted.
    """

    version = Migrate.Version(2, 3, 0)
    
    def cutover(self, dmd):
        log.info("Clearing heartbeats from devices that aren't collectors.")
        conn = dmd.ZenEventManager.connect()
        curr = conn.cursor()
        curr.execute("delete from heartbeat where device not in ('%s')" %
                "','".join(dmd.Monitors.getPerformanceMonitorNames()))

monitorAsHeartbeatDevice()
