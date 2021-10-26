#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import argparse
import json
import MySQLdb
import logging
import os
import re
import string
import sys
import time

from gather import ServiceMetrics, MetricGatherer

log = logging.getLogger('zenoss.servicemetrics')
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log.setLevel(logging.INFO)


class MysqlStats(ServiceMetrics):
    def __init__(self, options):
        super(MysqlStats, self).__init__(options)
        self.db = options.db

    def build_gatherer(self):
        return MysqlStatsGatherer(self.db)


class MysqlStatsGatherer(MetricGatherer):

    def __init__(self, db):
        self.global_config = os.environ['ZENHOME'] + '/etc/global.conf'
        self.db = db
        log.debug("Collecting for database: %s", self.db)
        self.config = self._get_global_conf()
        #DS name is stripped in RMMon ZEN-31546
        self.prefix = 'zenoss.db.' + self.db + '_'
        self.tags = {'internal': 'true'}

    def _get_global_conf(self):
        # return default config if config missing
        config = {
            'zodb-host': '127.0.0.1',
            'zodb-port': '3306',
            'zodb-user': 'zenoss',
            'zodb-password': 'zenoss',
            'zep-host': '127.0.0.1',
            'zep-port': '3306',
            'zep-user': 'zenoss',
            'zep-password': 'zenoss'}

        with open(self.global_config, 'r') as fp:
            lines = fp.readlines()
            for line in lines:
                option = line.split(' ')
                if len(option) == 2 and option[0].lower() in config:
                    config[option[0].lower()] = option[1].strip('\n')
            log.debug("Configuration is: %s" % config)
            return config

    def get_metrics(self):
        metrics = []
        # database queries
        _ZODB_OBJECTS_QUERY = 'SELECT count(zoid) from object_state'
        _INNODB_STATUS_QUERY = 'SHOW ENGINE INNODB STATUS'
        _BUFFER_POOL_QUERY = "SELECT FORMAT(DataPages*100.0/TotalPages,2) FROM \
        (SELECT variable_value DataPages FROM information_schema.global_status \
        WHERE variable_name = 'Innodb_buffer_pool_pages_data') AS A, \
        (SELECT variable_value TotalPages FROM information_schema.global_status \
        WHERE variable_name = 'Innodb_buffer_pool_pages_total') AS B"

        # Connect to MariaDB
        try:
            mysql_connection = MySQLdb.connect(host=self.config[self.db + '-host'],
                                               port=int(self.config[self.db + '-port']),
                                               user=self.config[self.db + '-user'],
                                               passwd=self.config[self.db + '-password'],
                                               db=self.db if self.db == 'zodb' else 'zenoss_zep',
                                               connect_timeout=5)
            mysql_cursor = mysql_connection.cursor()
        except MySQLdb.Error as e:
            log.error("Error connecting to MySQL: %s", e)
            if mysql_connection:
                mysql_connection.close()
            return metrics
        except KeyError:
            # Config in dict missing
            log.error("Unable to read config vars")
            return metrics

        # ZODB object count
        if self.db == 'zodb':
            zoids = self._query(mysql_cursor, _ZODB_OBJECTS_QUERY)
            metrics.extend(self._extract_zodb_objects(zoids))

        # buffer pool usage
        buff_usage = self._query(mysql_cursor, _BUFFER_POOL_QUERY)
        metrics.extend(self._extract_buffer_pool_usage(buff_usage))

        # innodb engine variables
        innodb_stats = self._query(mysql_cursor, _INNODB_STATUS_QUERY)
        metrics.extend(self._extract_innodb_engine_stats(innodb_stats))

        if mysql_connection:
            mysql_connection.close()
        log.info("Collected %i metrics" % len(metrics))
        log.debug("Metrics: %s" % metrics)
        return metrics

    def _query(self, mysql_cursor, query):
        result = None
        try:
            mysql_cursor.execute(query)
            result = mysql_cursor.fetchall()
        except MySQLdb.Error as e:
            log.error("Error exeucting query: %s, error: %s" % (query, e))
            return None
        log.debug("Query %s result: %s" % (query, result))
        return result

    def _extract_zodb_objects(self, result):
        metrics = []
        ts = time.time()

        try:
            result = int(result[0][0])
        except IndexError:
            log.error("Unable to parse query output: %s" % result)
            return metrics
        metrics.append(
            self.build_metric(
                self.prefix + 'objects',
                result,
                ts,
                self.tags))
        return metrics

    def _extract_innodb_engine_stats(self, result):
        metrics = []
        ts = time.time()

        try:
            result = result[0][2]
        except IndexError:
            log.error("Unable to parse query output: %s" % result)

        # History List Length
        hist_list_len = 'History list length '
        loc = string.find(result, hist_list_len)
        if loc != -1:
            # history length found
            metrics.append(self.build_metric(self.prefix + 'history_list_length', int(
                string.split(result[loc + len(hist_list_len):], '\n')[0]), ts, self.tags))

        # Active Transactions
        active_transactions = re.findall("---TRANSACTION.*ACTIVE", result)
        metrics.append(self.build_metric(self.prefix + 'active_transactions',
                                         len(active_transactions),
                                         ts,
                                         self.tags))

        # Transaction > 100 seconds
        long_transactions_running = re.findall(
            "---TRANSACTION.*ACTIVE [0-9]{3,} sec", result)
        metrics.append(self.build_metric(self.prefix + 'long_running_transactions',
                                         len(long_transactions_running),
                                         ts,
                                         self.tags))
        return metrics

    def _extract_buffer_pool_usage(self, result):
        metrics = []
        ts = time.time()

        try:
            result = float(result[0][0])
        except IndexError:
            log.error("Unable to parse query output: %s" % result)
            return metrics
        metrics.append(
            self.build_metric(
                self.prefix + 'buffer_pool_used_percentage',
                result,
                ts,
                self.tags))
        return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=60, help="polling interval in seconds")
    parser.add_argument("-d", "--database", dest="db", type =str,
                        default='zep', help="Collect database: zep or zodb")
    parser.add_argument("-v", "--verbose", dest="verbose", action='store_true',
                       help="Run metrics collection once in full debug and dump to stdout.")

    args = parser.parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)
        stdout = logging.StreamHandler(sys.stdout)
        log.addHandler(stdout)
        mstats = MysqlStats(options=args)
        mstats.run()
    else:
        mstats = MysqlStats(options=args)
        mstats.run()
