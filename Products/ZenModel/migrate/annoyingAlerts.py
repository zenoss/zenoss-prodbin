###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Add lastSent to alert_state.

'''
import Migrate

class AnnoyingAlerts(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        return
        conn = dmd.ZenEventManager.connect()
        c = conn.cursor()
        c.execute('describe alert_state')
        if 'lastSent' not in [x[0] for x in c.fetchall()]:
            c.execute('alter table alert_state '
                      'add column (lastSent timestamp)')
            
AnnoyingAlerts()
