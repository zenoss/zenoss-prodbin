from Acquisition import aq_base

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

for evt in dmd.Events.getSubEventClasses():
    convert(evt)
    for inst in evt.getInstances():
        convert(evt)

if hasattr(aq_base(evt), 'zEventProperties'):
    dmd.Events._delProperty("zEventProperties")
if hasattr(aq_base(evt), 'zEvent_severity'):
    dmd.Events._delProperty("zEvent_severity")
