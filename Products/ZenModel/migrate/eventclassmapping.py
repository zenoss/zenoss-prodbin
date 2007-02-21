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
    FOR EACH ROW INSERT INTO history SET
            dedupid=OLD.dedupid,
            evid=OLD.evid,
            device=OLD.device,
            component=OLD.component,
            eventClass=OLD.eventClass,
            eventKey=OLD.eventKey,
            summary=OLD.summary,
            message=OLD.message,
            severity=OLD.severity,
            eventState=OLD.eventState,
            eventClassKey=OLD.eventClassKey,
            eventGroup=OLD.eventGroup,
            stateChange=OLD.stateChange,
            firstTime=OLD.firstTime,
            lastTime=OLD.lastTime,
            count=OLD.count,
            prodState=OLD.prodState,
            suppid=OLD.suppid,
            manager=OLD.manager,
            agent=OLD.agent,
            DeviceCLass=OLD.DeviceClass,
            Location=OLD.Location,
            Systems=OLD.Systems,
            DeviceGroups=OLD.DeviceGroups,
            ipAddress=OLD.ipAddress,
            facility=OLD.facility,
            priority=OLD.priority,
            ntevid=OLD.ntevid,
            ownerid=OLD.ownerid,
            deletedTime=NULL,
            clearid=OLD.clearid,
            DevicePriority=OLD.DevicePriority,
            eventClassMapping=OLD.eventClassMapping
            ;
            """
            



class EventClassMapping(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        from Products.ZenEvents.DbConnectionPool import DbConnectionPool
        cpool = DbConnectionPool()
        conn = cpool.get(backend=dmd.ZenEventManager.backend, 
                        host=dmd.ZenEventManager.host, 
                        port=dmd.ZenEventManager.port, 
                        username=dmd.ZenEventManager.username, 
                        password=dmd.ZenEventManager.password, 
                        database=dmd.ZenEventManager.database)
        curs = conn.cursor()
        try:
            tables = ('status', 'history')
            for table in tables:
                curs.execute('desc %s' % table)
                r = curs.fetchall()
                if not [f for f in r if f[0] == 'eventClassMapping']:
                    curs.execute('alter table %s ' % table +
                                'add column eventClassMapping '
                                'varchar(128) default ""')
            try:
                curs.execute('drop trigger status_delete')
            except OperationalError:
                pass
            curs.execute(trigger)
        finally:
            curs.close()
            cpool.put(conn)

EventClassMapping()
