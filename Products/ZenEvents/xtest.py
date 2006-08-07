#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''Bench-test script for zenxevents

$Id$
'''

import xmlrpclib
import time

s = xmlrpclib.ServerProxy('http://localhost:8081/', encoding='iso-8859-1')
# s = xmlrpclib.ServerProxy('http://admin:not2much@localhost:8080/zport/dmd/ZenEventManager')

event = dict(device='eros', 
	     eventClassKey = 'test',
	     eventClass = '/App',
             summary='This is \xfc new test event: %d' % time.time(),
             severity=4,
             component='xyzzy')
clear = event.copy()
clear.update(dict(severity=0, summary="All better now!"))

def main():
    "performance test"
    for i in range(100):
        s.sendEvents([event, clear])

def coverage():
    s.sendEvents([event, clear])
    s.sendEvent(event)
    issues = s.getDevicePingIssues()
    for i in issues:
        print i

def simple():
    s.sendEvent(event)
    time.sleep(30)
    s.sendEvent(clear)

simple()
