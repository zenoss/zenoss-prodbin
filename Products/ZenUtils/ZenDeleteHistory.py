#! /usr/bin/env python 
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""
ZenDeleteHistory performs cleanup and other maintenance tasks on the MySQL
events database.
"""

import logging
log = logging.getLogger('zen.deleteHistory')

import time
from math import ceil

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from _mysql_exceptions import OperationalError


DEFAULT_CHUNK_SIZE = 10000


class ZenDeleteHistory(ZenScriptBase):
    """
    Delete events and performance other maintenance tasks on the events
    database.
    """

    def buildOptions(self):
        self.parser.add_option('-n', '--numDays', dest='numDays',
            default=None,
            help='Number of days of history to keep')
        self.parser.add_option('--chunksize', dest='chunksize',
            default=DEFAULT_CHUNK_SIZE,
            help='Number of evids to delete in a single query')
        self.parser.add_option('-d', '--device', dest='device',
            action='append', default=[],
            help='Specific device for which to delete events (optional)')
        self.parser.add_option('--severity', dest='severity',
            action='append', default=[],
            help='Only delete events of this severity.')
        self.parser.add_option('--eventClass', dest='eventClass',
            action='append', default=[],
            help='Only delete events of this eventClass.')
        self.parser.add_option('--cleanup', dest='cleanup',
            action='store_true', default=False,
            help='Cleanup alert_state, log and detail tables')
        self.parser.add_option('--optimize', dest='optimize',
            action='store_true', default=False,
            help='Optimize tables after performing other operations')
        self.parser.add_option('--truncate', dest='truncate',
            action='store_true', default=False,
            help='Truncate (ERASE) entire history table')
        self.parser.add_option('--really', dest='really',
            action='store_true', default=False,
            help='You must be REALLY sure you want to truncate history')
        ZenScriptBase.buildOptions(self)


    def run(self):
        self.connect()

        if self.options.truncate:
            if self.options.really:
                self.options.cleanup = True
                self.truncateHistory()
            else:
                log.warn((
                    "Specifying the --truncate option will permanently erase "
                    "all archived events. You must specify the --really "
                    "option if you really want to do this."))
                return
        else:
            # Input validation for numDays option.
            if self.options.numDays:
                try:
                    self.options.numDays = int(self.options.numDays)
                except ValueError:
                    log.critical("numDays argument must be an interger")
                    return
            else:
                log.critical("The numDays argument must be provided")
                return

            # Input validation for severity option.
            if len(self.options.severity) > 0:
                severityMap = dict([(a, b) for a, b in \
                    self.dmd.ZenEventManager.severityConversions])

                severities = []
                for s in self.options.severity:
                    try:
                        severity = int(s)
                        if severity >= 0 and severity <= 5:
                            severities.append(severity)
                        else:
                            log.critical("Severity must be 0-5.")
                            return
                    except ValueError:
                        s = s.capitalize()
                        if s in severityMap:
                            severities.append(severityMap[s])
                        else:
                            log.critical("%s is not a valid severity.", s)
                            return

                self.options.severity = severities

            self.deleteHistory()

        if self.options.cleanup:
            self.cleanupTables()

        if self.options.optimize:
            self.optimizeTables()

        self.analyzeTables()


    def executeStatements(self, statements):
        """
        Executes a list of statements within a transaction.
        """
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            conn.autocommit(0)
            try:
                curs = conn.cursor()
                for statement in statements:
                    begin = time.time()
                    log.debug("Executing: %s", statement)
                    count = curs.execute(statement)
                    log.debug((
                        "Last statement took %.3f seconds to execute and "
                        "affected %s rows."), time.time() - begin, count)

                conn.commit()
            except OperationalError, ex:
                log.error('MySQL error: (%s) %s', ex.args[0], ex.args[1])
                log.error("Rolling back transaction.")
                conn.rollback()
        finally:
            conn.autocommit(1)
            zem.close(conn)


    def deleteHistory(self):
        """
        Deletes events more than X days old where X is the number specified by
        the "numDays" command line argument. Optionally restricts the
        deletion to the device specified with the "device" command line
        argument.
        """
        begin = time.time()
        earliest_time = time.time() - (86400 * self.options.numDays)

        device_filter = ""
        if len(self.options.device) > 0:
            log.info("Deleting historical events older than %s days for %s.",
                self.options.numDays, self.options.device)
            device_filter = " AND device IN (%s)" % ','.join([
                "'%s'" % d for d in self.options.device])
        else:
            log.info("Deleting historical events older than %s days.",
                self.options.numDays)

        severity_filter = ""
        if len(self.options.severity) > 0:
            severity_filter = " AND severity IN (%s)" % ','.join(
                map(str, self.options.severity))
        
        eventClass_filter = ""
        if len(self.options.eventClass) > 0:
            eventClass_filter = " AND eventClass IN (%s)" % ','.join([
                "'%s'" % d for d in self.options.eventClass])

        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            conn.autocommit(0)
            try:
                curs = conn.cursor()
                
                # Create temp table containing events to delete
                log.info("Building list of events to delete.")
                curs.execute("DROP TABLE IF EXISTS delete_evids")
                curs.execute(
                    "CREATE TEMPORARY TABLE delete_evids "
                    "SELECT evid FROM history WHERE lastTime < %s%s%s%s" % (
                        earliest_time, device_filter, severity_filter,eventClass_filter))

                curs.execute("CREATE INDEX evid ON delete_evids (evid)")
                curs.execute("SELECT COUNT(evid) FROM delete_evids")
                total_events = curs.fetchone()[0]

                if self.options.chunksize <= 0:
                    self.options.chunksize = DEFAULT_CHUNK_SIZE
                total_chunks = int(ceil(total_events  * 1.0 / self.options.chunksize))
                start_time = time.time()

                # chunk and remaining_time are used to commit deletes more often
                # and inform the user, via log output, of the status of the
                # query. You can often see large deletes, with thousands or
                # millions of rows that take many hours to run, and can slow
                # down zenoss performance. This splits the job into chunks, so
                # that commits are done often enough that if the job is taking
                # lots of time, you can stop in the middle of the delete and
                # some events will be gone. Also, time remaining is given to
                # the user, so that the user may estimate down time.
                chunk = 0
                remaining_time = None
                while chunk < total_chunks:
                    if remaining_time is not None:
                        log.info(
                            "Deleting chunk %s/%s. %1.1f seconds remaining",
                            chunk+1, total_chunks, remaining_time)
                    else:
                        log.info(
                            "Deleting chunk %s/%s.",
                            chunk+1, total_chunks)

                    # Determine events in chunk
                    curs.execute("DROP TABLE IF EXISTS delete_evids_chunk")
                    curs.execute(
                        "CREATE TEMPORARY TABLE delete_evids_chunk "
                        "SELECT evid FROM delete_evids LIMIT %s,%s" % (
                            chunk*self.options.chunksize,
                            self.options.chunksize))

                    # Delete chunked events from tables
                    for table in ("history", "detail", "log", "alert_state"):
                        curs.execute(
                            "DELETE t FROM %s t RIGHT JOIN "
                            "delete_evids_chunk d ON d.evid = t.evid" % table)

                    conn.commit()
                    chunk += 1
                    elapsed_time = time.time() - start_time
                    remaining_time = \
                        float(elapsed_time / chunk) * (total_chunks - chunk)

                curs.execute("DROP TABLE IF EXISTS delete_evids")
                conn.commit()
            except OperationalError, ex:
                log.error('MySQL error: (%s) %s', ex.args[0], ex.args[1])
                log.error("Rolling back transaction.")
                conn.rollback()
        finally:
            conn.autocommit(1)
            zem.close(conn)

        log.info("Historical event deletion took %.3f seconds.",
            time.time() - begin)


    def truncateHistory(self):
        """
        Truncates the entire history table. This will also force a cleanup run
        to delete all orphaned rows in the accessory tables.
        """
        log.info("Truncating history table.")

        statements = [
            "TRUNCATE TABLE history",
            ]

        begin = time.time()
        self.executeStatements(statements)
        log.info("History table truncated in %.3f seconds.",
            time.time() - begin)


    def cleanupTables(self):
        """
        Cleans up the detail, log and alert_state accessory tables. If events
        are deleted from the history table without considering these tables,
        rows can be orphaned. This method cleans up these orphaned rows.
        """
        log.info("Cleaning up orphaned rows in accessory tables.")

        statements = [
            "DROP TABLE IF EXISTS cleanup_evids",
            "CREATE TEMPORARY TABLE cleanup_evids SELECT evid FROM status",
            "INSERT INTO cleanup_evids SELECT evid FROM history",
            "CREATE INDEX evid ON cleanup_evids (evid)",
            ]

        for table in ("log", "detail", "alert_state"):
            statements.append((
                "DELETE t FROM cleanup_evids c "
                "RIGHT JOIN %s t USING (evid) WHERE c.evid IS NULL" % table))

        statements.append("DROP TABLE IF EXISTS cleanup_evids")

        begin = time.time()
        self.executeStatements(statements)
        log.info("Accessory tables cleaned up in %.3f seconds.",
            time.time() - begin)


    def optimizeTables(self):
        """
        Manually optimizing tables after large amounts of rows have been
        deleted can improve their performance and reclaim unused space.
        
        NOTE: Optimizing a table places a write-lock on it, and it can be a
              lengthy process.
        """
        log.info("Optimizing tables to reclaim unused space.")

        statements = [
            "OPTIMIZE TABLE alert_state, status, log, detail, history",
            ]

        begin = time.time()
        self.executeStatements(statements)
        log.info("Tables optimized in %.3f seconds.", time.time() - begin)


    def analyzeTables(self):
        """
        Manually analyzing tables is recommended after large deletions so that
        the optimizer can plan queries properly.
        
        NOTE: Analyzing an InnoBD tables places a write-lock on it. However,
              this is typically a quick process.
        """
        log.info("Analyzing tables for optimal queries.")

        statements = [
            "ANALYZE TABLE alert_state, status, log, detail, history",
            ]

        begin = time.time()
        self.executeStatements(statements)
        log.info("Tables analyzed in %.3f seconds.", time.time() - begin)


if __name__ == '__main__':
    zdh = ZenDeleteHistory()
    zdh.run()
