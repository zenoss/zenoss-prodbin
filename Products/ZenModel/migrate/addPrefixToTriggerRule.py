##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add 'evt.' prefix to trigger rules and custom fields definition
in order to make possible evaluate trigger rules with them.
 
'''

import Migrate
from zenoss.protocols.jsonformat import from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventDetailItemSet
import zenoss.protocols.protobufs.zep_pb2 as zep
from Products.Zuul import getFacade

class addPrefixToTriggerRule(Migrate.Step):
    version = Migrate.Version(5, 0, 70)
    
    def cutover(self, dmd):
        zepf = getFacade('zep')
        trigf = getFacade('triggers')

        details = zepf.getUnmappedDetails()

        for detail in details:
            if not detail['key'].startswith("evt."):
                old_detail = detail['key']
                zepf.removeIndexedDetail(detail['key'])
                detail['key'] = "evt.%s" % detail['key']
                detailItemSet = from_dict(EventDetailItemSet, dict(details=[detail]))
                zepf.addIndexedDetails(detailItemSet)
        
                triggers = trigf.getTriggers()
                for trigger in triggers:
                    if old_detail in trigger['rule']['source']: 
                        old_rule = str(trigger['rule']['source']).replace(old_detail, detail['key'])
                        trigger['rule']['source'] = old_rule
                        trigf.updateTrigger(**trigger)



addPrefixToTriggerRule()
