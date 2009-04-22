###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Add zSshConcurrentSessions to /Devices.

'''
import Migrate

class zSshConcurrentSessions(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        # Install the zSshConcurrentSessions zProperty
        if not dmd.Devices.hasProperty('zSshConcurrentSessions'):
            dmd.Devices._setProperty('zSshConcurrentSessions', 10, type="int")

zSshConcurrentSessions()

