#! /usr/bin/env python 
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""
ZenDeleteHistory performs cleanup and other maintenane tasks on the MySQL
events database.
"""

import logging
log = logging.getLogger('zen.deleteHistory')

import time

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from _mysql_exceptions import OperationalError


class ZenDeleteHistory(ZenScriptBase):
    """
    Delete events and performance other maintenance tasks on the events
    database.
    """

    def buildOptions(self):
        self.parser.add_option('-n', '--numDays', dest='numDays',
            default=None,
            help='Number of days of history to keep')
        self.parser.add_option('-d', '--device', dest='device',
            action='append', default=[],
            help='Specific device for which to delete events (optional)')
        self.parser.add_option('--severity', dest='severity',
            action='append', default=[],
            help='Only delete events of this severity.')
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

        statements = [
            "DROP TABLE IF EXISTS delete_evids",
            ("CREATE TEMPORARY TABLE delete_evids "
             "SELECT evid FROM history WHERE lastTime < %s%s%s" % (
                earliest_time, device_filter, severity_filter)),
            "CREATE INDEX evid ON delete_evids (evid)",
            ]

        for table in ("history", "detail", "log", "alert_state"):
            statements.append((
                "DELETE t FROM %s t "
                "RIGHT JOIN delete_evids d ON d.evid = t.evid" % table))

        statements.append("DROP TABLE IF EXISTS delete_evids")

        begin = time.time()
        self.executeStatements(statements)
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
