#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add a DevicePriority column to the status and history tables

'''

__version__ = "$Revision$"[11:-2]

import Migrate
from MySQLdb import OperationalError
import MySQLdb.constants.ER as ER
MYSQL_ERROR_TRIGGER_DOESNT_EXIST = 1360

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
            OLD.clearid,
            OLD.DevicePriority
            )"""
            


class DevicePriority(Migrate.Step):
    "Add a DevicePriority column to the status and history tables"
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        try:
            zem = self.dmd.ZenEventManager
            conn = zem.connect()
            curs = conn.cursor()
            cmd = 'ALTER TABLE %s ADD COLUMN ' + \
                  '(DevicePriority smallint(6) default 3)'
            for table in ('status', 'history'):
                try:
                    curs.execute(cmd % table)
                except OperationalError, e:
                    if e[0] != ER.DUP_FIELDNAME:
                        raise
            try:
                curs.execute('DROP TRIGGER status_delete')
            except OperationalError, e:
                if e[0] != MYSQL_ERROR_TRIGGER_DOESNT_EXIST:
                    raise
            curs.execute(trigger)
        finally: zem.close(conn)

DevicePriority()
