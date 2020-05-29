##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from zope.component import subscribers

from Products.DataCollector.ApplyDataMap import isSameData
from Products.ZenUtils.guid.interfaces import IGUIDManager

from ZenPacks.zenoss.Impact.impactd.interfaces import IRelationshipDataProvider
from Products.ZenNub.db import get_nub_db

db = get_nub_db()
log = logging.getLogger('zen.zennub.impact')



def test_impact():
    for device_id in db.devices:
        mapper = db.get_mapper(device_id)

        for obj_id, _ in mapper.all():
            zobj = db.get_zobject(device=device_id, component=obj_id)
            impacted_by, impacting = impacts_for(zobj)

            if len(impacted_by) + len(impacting) == 0:
                log.info("[%s] no impacts" % zobj)
            else:
                log.info("[%s] impacted_by=%s" % (zobj, impacted_by))
                log.info("[%s] impacting=%s" % (zobj, impacting))

def update_all_impacts():
    changed = False
    for device_id in db.devices:
        mapper = db.get_mapper(device_id)
        for component_id, _ in mapper.all():
            if update_impact(device=device_id, component=component_id):
                changed = True

    return changed

def update_impact(device=None, component=None):
    zobj = db.get_zobject(device=device, component=component)
    impacted_by, impacting = impacts_for(zobj)
    impacted_dims = []
    for i in impacted_by:
        dimlist = []
        for k,v in i.dimensions().iteritems():
            dimlist.append("%s=%s" % (k,v))
        impacted_dims.append(",".join(sorted(dimlist)))

    impacting_dims = []
    for i in impacting:
        dimlist = []
        for k,v in i.dimensions().iteritems():
            dimlist.append("%s=%s" % (k,v))
        impacting_dims.append(",".join(sorted(dimlist)))

    changed = False
    if not isSameData(impacted_dims, zobj.impactFromDimensions):
        zobj.impactFromDimensions = impacted_dims
        changed = True

    if not isSameData(impacting_dims, zobj.impactToDimensions):
        zobj.impactToDimensions = impacting_dims
        changed = True

    if component == 'emc-vnx1_CLARiiON_APM00141704021_SP_A':
        import pdb; pdb.set_trace()

    return changed

def impacts_for(thing):
    '''
    Return a two element tuple.

    First element is a list of objects impacted by thing. Second element is
    a list of objects impacting thing.
    '''

    impacted_by = []
    impacting = []

    guid_manager = IGUIDManager(thing.getDmd())
    for subscriber in subscribers([thing], IRelationshipDataProvider):
        try:
            edges = list(subscriber.getEdges())
        except Exception, e:
            log.error("Unable to get edges from %s: %s" % (subscriber, e))
            continue

        for edge in edges:
            source = guid_manager.getObject(edge.source)
            impacted = guid_manager.getObject(edge.impacted)
            if source.id == thing.id:
                impacting.append(impacted)
            elif impacted.id == thing.id:
                impacted_by.append(source)
    return (impacted_by, impacting)
