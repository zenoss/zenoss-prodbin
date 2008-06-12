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

class WinModelerUnderModeler(Migrate.Step):

    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        import os
        from Products.ZenUtils.Utils import binPath
        os.system('%s stop >/dev/null 2>&1' % binPath('zenwinmodeler'))
        conn = dmd.ZenEventManager.connect()
        curr = conn.cursor()
        curr.execute("delete from heartbeat where component = 'zenwinmodeler'")

WinModelerUnderModeler()
