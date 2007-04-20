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

Rename the property "zEvent_severity" to zEventSeverity and
remove zEventProperties from all events.

'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate

def convert(evt):
    if hasattr(aq_base(evt), 'zEvent_severity'):
        try:
            sev = int(evt.zEvent_severity)
            if not hasattr(aq_base(evt), 'zEventSeverity'):
                evt._setProperty('zEventSeverity', sev, type='int')
        except ValueError:
            print sev
        evt._delProperty('zEvent_severity')
    if hasattr(aq_base(evt), 'zEventProperties'):
        evt._delProperty('zEventProperties')



class EvtProps(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        for evt in dmd.Events.getSubEventClasses():
            convert(evt)
            for inst in evt.getInstances():
                convert(inst)
        convert(dmd.Events)

EvtProps()
