#!/usr/bin/env python
#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################

import time
import Globals
from Products.ZenEvents.Schedule import Schedule
from Products.ZenEvents.ActionRule import ActionRule

print "Adjusting schedules for daylight savings time."
print "%s %s" % ('-'*57, '-'*21)

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
dmd = ZenScriptBase(connect=True).dmd

s = Schedule(None, dmd)
for next, window in s.makeWorkList(time.time(), s.getWindows()):
    nextList = time.localtime(next)
    startList = time.localtime(window.start)
    target = window.target()
    windowString = "%s on " % window.id
    if isinstance(target, ActionRule):
        windowString += "%s/%s" % (target.getUserid(), target.getId())
    else:
        windowString += target.getId()
    if nextList[3] == startList[3]:
        print "%56s: No adjustment needed." % windowString
    elif nextList[3] == (startList[3] - 1) or \
        (nextList[3] == 23 and startList[3] == 0):
        print "%56s: Fall back." % windowString
        window.start = next + 3600
    elif nextList[3] == (startList[3] + 1) or \
        (nextList[3] == 0 and startList[3] == 23):
        print "%56s: Spring forward." % windowString
        window.start = next - 3600

import transaction
trans = transaction.get()
trans.note("fixSchedulesForDST")
trans.commit()
