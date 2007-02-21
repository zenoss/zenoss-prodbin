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

    def execute(self, s, cmd):
        from MySQLdb import OperationalError
        try:
            s.execute(cmd)
        except OperationalError:
            pass

    def cutover(self, dmd):
        from Products.ZenEvents.DbConnectionPool import DbConnectionPool
        cpool = DbConnectionPool()
        conn = cpool.get(backend=self.dmd.ZenEventManager.backend, 
                        host=self.dmd.ZenEventManager.host, 
                        port=self.dmd.ZenEventManager.port, 
                        username=self.dmd.ZenEventManager.username, 
                        password=self.dmd.ZenEventManager.password, 
                        database=self.dmd.ZenEventManager.database)
        curs = conn.cursor()
        try:
            cmd = 'ALTER TABLE %s ADD COLUMN ' + \
                  '(DevicePriority smallint(6) default 3)'
            self.execute(curs, cmd % 'status')
            self.execute(curs, cmd % 'history')
            self.execute(curs, 'DROP TRIGGER status_delete')
            self.execute(curs, trigger)
        finally:
            curs.close()
            cpool.put(conn)

DevicePriority()
