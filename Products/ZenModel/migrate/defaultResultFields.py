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
__doc__='''

Add eventState and severity as default result fields.

'''
import Migrate

class AddResultFields(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zem = dmd.ZenEventManager
        for attr in ('DeviceResultFields', 'ComponentResultFields',
                     'defaultResultFields'):
            curfields = list(getattr(zem, attr))
            if 'eventState' not in curfields:
                curfields.insert(0, 'eventState')
            if 'severity' not in curfields:
                curfields.insert(1, 'severity')
            setattr(zem, attr, tuple(curfields))

AddResultFields()


