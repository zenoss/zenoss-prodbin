#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import argparse
import logging
import subprocess
import time
from collections import Counter

from gather import MetricGatherer, ServiceMetrics


log = logging.getLogger('zenoss.servicemetrics')
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log.setLevel(logging.INFO)


class StorageMetrics(ServiceMetrics):

    def __init__(self, options):
        super(StorageMetrics, self).__init__(options)
        self.name = options.name

    def build_gatherer(self):
        return StorageMetricGatherer(self.name)


class StorageMetricGatherer(MetricGatherer):
    METRICS_QUERY = "/opt/zenoss/bin/metrics/mysqlmetrics.sh"

    def __init__(self, name):
        MetricGatherer.__init__(self)
        self.name = name

    def get_metrics(self):
        metrics = []
        ts = time.time()
        tags = {'zenoss_storage': self.name}
        try:
            response = subprocess.check_output([self.METRICS_QUERY, self.name])
        except Exception as e:
            log.error("Error gathering mysql storage info: %s" % e)
            return []
        total_size = 0
        for line in response.split('\n'):
            if not line:
                continue
            parsed = line.split('\t')
            table, size, free = parsed[0], parsed[1], parsed[2]
            table_size = 'zenoss.%s.%s.size' % (self.name, table)
            table_free = 'zenoss.%s.%s.free' % (self.name, table)
            total_size += int(size)
            metrics.append(self.build_metric(table_size, size, ts, tags))
            metrics.append(self.build_metric(table_free, free, ts, tags))
        metrics.append(self.build_metric('zenoss.%s.total.size' % self.name, total_size, ts, tags))

        total, byscript = _get_connection_info()
        metrics.append(self.build_metric('zenoss.%s.connection_info.total' % self.name, total, ts, tags))
        for k, v in byscript.items():
            tgk = {'zenoss_daemon': k}
            tgk.update(tags)
            metrics.append(self.build_metric('zenoss.%s.connection_info.rate' % self.name, v, ts, tgk))

        return metrics


def _get_connection_info():
    """
    Get the info field from connection_info table for recent time (see connection_info.sh),
    Get name of the script that caused the connection to the DB from the traceback (info field).
    :return:
        total: the total number of new connections for last n min.
        counter: it's a dictionary where the key is the name of the script that caused the connection to DB, value is the number of connections.
    """
    try:
        response = subprocess.check_output("/opt/zenoss/bin/metrics/connection_info.sh")
    except Exception as e:
        log.error("Error gathering mysql connection info: %s" % e)
        return 0, {}

    total = 0
    counter = Counter()

    for line in response.split('\n'):
        if not line: continue
        lines = line.split()
        try:
            ind = lines.index("File")
        except ValueError:
            continue

        script_name = lines[ind+1]
        slash = script_name.rfind('/')
        point = script_name.rfind('.')
        if slash >= 0 and point >= 0:
            script_name = script_name[slash+1:point]
        total += 1
        counter[script_name] += 1
    return total, counter


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    parser.add_argument("name", type=str, default=30, help="name of service monitored")
    args = parser.parse_args()

    rm = StorageMetrics(options=args)
    rm.run()

