#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Rename the property "zEvent_severity" to zEventSeverity and
remove zEventProperties from all events.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate

def convert(evt):
    if hasattr(aq_base(evt), 'zEvent_severity'):
        try:
            sev = int(evt.zEvent_severity)
            evt._setProperty('zEventSeverity', sev, type='int')
        except ValueError:
            print sev 
        evt._delProperty('zEvent_severity')
    if hasattr(aq_base(evt), 'zEventProperties'):
        evt._delProperty('zEventProperties')



class EvtProps(Migrate.Step):
    version = 20.0

    def cutover(self, dmd):
        for evt in dmd.Events.getSubEventClasses():
            convert(evt)
            for inst in evt.getInstances():
                convert(evt)

        if hasattr(aq_base(dmd.Events), 'zEventProperties'):
            dmd.Events._delProperty("zEventProperties")
        if hasattr(aq_base(dmd.Events), 'zEvent_severity'):
            dmd.Events._delProperty("zEvent_severity")

EvtProps()
