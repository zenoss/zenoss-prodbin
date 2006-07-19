#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Re-index the event history table.

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
    version = 22.0

    def execute(self, s, cmd):
        from MySQLdb import OperationalError
        try:
            s.execute(cmd)
        except OperationalError:
            pass

    def cutover(self, dmd):
        c = dmd.ZenEventManager.connect()
        s = c.cursor()
        cmd = 'ALTER TABLE %s ADD COLUMN (clearid char(25))'
        self.execute(s, cmd % 'status')
        self.execute(s, cmd % 'history')
        self.execute(s, 'DROP TRIGGER status_delete')
        self.execute(s, trigger)

ClearId()
