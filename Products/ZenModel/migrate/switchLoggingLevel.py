#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Switch default logging level to WARN
"""

import logging
log = logging.getLogger("zen.migrate")
import os
import sys
import json
import subprocess


DEVNULL = open(os.devnull, 'w')


def main():
    log.info("Looking up service CentralQuery")
    try:
        svc_json = subprocess.check_output(["serviced", "service", "list", "CentralQuery"])
        parsed = json.loads(svc_json)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except ValueError:
        sys.exit(1)
    log.info("Updating default logging level")
    parsed['logging']['level'] = 'WARN'
    parsed['logging']['loggers']['org.zenoss'] = 'WARN'
    try:
        proc = subprocess.Popen(["serviced", "service", "edit", "CentralQuery"], stdin=subprocess.PIPE, stdout=DEVNULL)
        proc.communicate(json.dumps(parsed))
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
