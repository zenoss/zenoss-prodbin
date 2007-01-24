#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='Add eventClassMapping to status and history tables'

import Migrate
from MySQLdb import OperationalError
import logging
log = logging.getLogger("zen.migrate")

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
            OLD.DevicePriority,
            OLD.eventClassMapping
            )"""
            



class EventClassMapping(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        conn = dmd.ZenEventManager.connect()
        try:
            tables = ('status', 'history')
            cur = conn.cursor()
            for table in tables:
                cur.execute('desc %s' % table)
                r = cur.fetchall()
                if not [f for f in r if f[0] == 'eventClassMapping']:
                    cur.execute('alter table %s ' % table +
                                'add column eventClassMapping '
                                'varchar(128) default ""')
            try:
                cur.execute('drop trigger status_delete')
            except OperationalError:
                pass
            cur.execute(trigger)
        finally:
            conn.close()
EventClassMapping()
