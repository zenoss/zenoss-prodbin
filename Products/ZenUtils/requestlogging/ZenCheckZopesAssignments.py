#!/usr/bin/env python

##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import Globals

from ZopeRequestLogger import ZopeRequestLogger

import subprocess
import re
import time
import datetime
import os
import sys
import redis
import argparse
import json
import pprint

SCRIPT_VERSION = '1.0.0'

'''------------------------ VERSION SUMMARY --------------------------------
 1.0.0 pending zope calls detected parsing start/end traces from log file
 1.1.0 pending zope calls detected using Redis. output less verbose
 -------------------------------------------------------------------------'''

REDIS_URL = ZopeRequestLogger.get_redis_url()

def get_redis_client():
        redis_client = ZopeRequestLogger.create_redis_client(REDIS_URL)
        if redis_client is None:
                msg = 'ERROR connecting to redis. redis URL: {0}'.format(REDIS_URL)
                print msg
                print 'Please check the redis-url value in global.conf'
                sys.exit(1)
        return redis_client


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version=SCRIPT_VERSION,
        description="Checks for unfinished Zope requests.",
        usage="""%(prog)s <command>

This program checks the status of the running zope processes.
    clear     Clears redis entries for zope requests.
    show      Shows outstanding zope requests.
""")
    parser.add_argument("command", help="command to execute")
    return parser.parse_args()

def clear_redis():
       redis_client = get_redis_client()
       pattern = '{0}*'.format(ZopeRequestLogger.REDIS_KEY_PATTERN)
       keys = redis_client.keys(pattern)
       redis_client.delete(*keys)

def print_all_not_finished_assigments():
       redis_client = get_redis_client()
       pattern = '{0}*'.format(ZopeRequestLogger.REDIS_KEY_PATTERN)
       keys = redis_client.keys(pattern)
       print '-'*50
       print 'Found {0} unfinished requests'.format(len(keys))
       print '-'*50
       if keys:
               values = redis_client.mget(keys)
               for value in values:
                       pprint.pprint(json.loads(value))
                       print '-'*50

def main():
	""" """
	options = parse_options()

	if options.command == "clear":
		clear_redis()
		print "Pending requests cleared from redis"
		sys.exit(0)
        if options.command == "show":
                print_all_not_finished_assigments()
                sys.exit(0)

if __name__ == "__main__":
	main()

