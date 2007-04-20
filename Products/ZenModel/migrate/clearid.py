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

Add a clearid column to the status and history tables

'''

__version__ = "$Revision$"[11:-2]

import Migrate

trigger = """
    CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.dedupid,
            OLD.evid,
            OLD.device,
            OLD.component,
            OLD.eventClass,
            OLD.eventKey,
            OLD.summary,
            OLD.message,
            OLD.severity,
            OLD.eventState,
            OLD.eventClassKey,
            OLD.eventGroup,
            OLD.stateChange,
            OLD.firstTime,
            OLD.lastTime,
            OLD.count,
            OLD.prodState,
            OLD.suppid,
            OLD.manager,
            OLD.agent,
            OLD.DeviceClass,
            OLD.Location,
            OLD.Systems,
            OLD.DeviceGroups,
            OLD.ipAddress,
            OLD.facility,
            OLD.priority,
            OLD.ntevid,
            OLD.ownerid,
            NULL,
            OLD.clearid
            )"""
            


class ClearId(Migrate.Step):
    "Add a clearid column to the status and history tables"
    version = Migrate.Version(0, 22, 0)

    def execute(self, s, cmd):
        from MySQLdb import OperationalError
        try:
            s.execute(cmd)
        except OperationalError:
            pass

    def cutover(self, dmd):
        try:
            zem = self.dmd.ZenEventManager
            conn = zem.connect()
            curs = conn.cursor()
            cmd = 'ALTER TABLE %s ADD COLUMN (clearid char(25))'
            self.execute(curs, cmd % 'status')
            self.execute(curs, cmd % 'history')
            self.execute(curs, 'DROP TRIGGER status_delete')
            self.execute(curs, trigger)
        finally: zem.close(conn)


ClearId()
