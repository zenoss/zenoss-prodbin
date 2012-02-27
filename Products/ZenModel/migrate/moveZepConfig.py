###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """Move some parameters from zeneventserver.conf to ZepConfig so
changing them doesn't require a restart.
"""
import os
import logging
import Globals
from Products.ZenUtils.Utils import unused, zenPath
from Products.ZenModel.migrate import Migrate
from Products.Zuul import getFacade

unused(Globals)

log = logging.getLogger('zen.migrate')

class moveZepConfig(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    # translates zeneventserver.conf key to ZenConfig protocol buffer key
    _params = {"zep.aging.interval_milliseconds": "aging_interval_milliseconds",
               "zep.aging.limit": "aging_limit",
               "zep.archive.interval_milliseconds": "archive_interval_milliseconds",
               "zep.archive.limit": "archive_limit",
               "zep.index.summary.interval_milliseconds": "index_summary_interval_milliseconds",
               "zep.index.archive.interval_milliseconds": "index_archive_interval_milliseconds",
               "zep.index.limit": "index_limit",
              }

    def _read_from_conf(self, zeneventserver_conf):
        with open(zeneventserver_conf) as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("=")]
                if len(parts) != 2:
                    continue
                key, value = parts
                for param in self._params:
                    if key == param:
                        yield self._params[key], value
                        break

    def cutover(self, dmd):
        zeneventserver_conf = zenPath("etc", "zeneventserver.conf")
        if not os.path.exists(zeneventserver_conf):
            return
        log.info("Moving parameters from zeneventserver.conf to zenoss_zep config table.")
        values = {}
        for config_name, config_value in self._read_from_conf(zeneventserver_conf):
            values[config_name] = config_value
        zep = getFacade('zep')
        zep.setConfigValues(values)

moveZepConfig()
