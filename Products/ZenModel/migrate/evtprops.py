#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
    version = Migrate.Version(0, 20, 0)

    def cutover(self, dmd):
        for evt in dmd.Events.getSubEventClasses():
            convert(evt)
            for inst in evt.getInstances():
                convert(inst)
        convert(dmd.Events)

EvtProps()
