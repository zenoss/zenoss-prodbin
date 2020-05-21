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

from Products.ZenUtils.guid.interfaces import IGUIDManager
from ZenPacks.zenoss.Impact.impactd.interfaces import IRelationshipDataProvider

log = logging.getLogger('zen.zennub.impact')


def test_impact(db):
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
                impacted_by.append(impacted)
            elif impacted.id == thing.id:
                impacting.append(source)
    return (impacted_by, impacting)
