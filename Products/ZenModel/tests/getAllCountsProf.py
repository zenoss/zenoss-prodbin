###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Zope2
app = Zope2.app()
devs = app.zport.dmd.Devices.getOrganizer("/Server")

import hotshot, hotshot.stats

def runtest():
    prof = hotshot.Profile("allcounts.prof")
    prof.runcall(devs.getAllCounts)
    prof.close()

def showresults():
    stats = hotshot.stats.load("allcounts.prof")
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(20)

#runtest()
#showresults()


