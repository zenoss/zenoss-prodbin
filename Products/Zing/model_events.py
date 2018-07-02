##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time

from zope.component import adapter
from itertools import chain
from logging import getLogger

from Products.ZenMessaging.ChangeEvents.interfaces import IMessagePostPublishingEvent
from Products.Zuul.utils import get_dmd
from Products.Zing.interfaces import IZingConnectorProxy
from Products.Zing.fact import device_organizers_fact
from Products.ZenUtils.guid.interfaces import IGUIDManager

from zenoss.protocols.protobufs.modelevents_pb2 import ModelEvent
from zenoss.protocols.protobufs import model_pb2 as MODELCONSTANTS

log = getLogger("zen.zing.events")

ORGANIZER_FACT_MODEL_EVENT_TYPES = { ModelEvent.ADDRELATION, ModelEvent.REMOVERELATION, ModelEvent.MOVED }

KWOWN_MODEL_TYPES = {'COMPONENT', 'DEVICE', 'ORGANIZER', 'SERVICE'}

class PostCommitModelEventProcessor(object):
    def __init__(self):
        dmd = get_dmd()
        self._guid_manager = IGUIDManager(dmd)
        self._zing_connector_client = IZingConnectorProxy(dmd)

    def _get_object(self, uuid):
        return self._guid_manager.getObject(uuid)

    def _get_uuid(cls, model_event):
        for model_type in KWOWN_MODEL_TYPES:
            if model_event.model_type == getattr(MODELCONSTANTS, model_type):
                return getattr(model_event, model_type.lower()).uuid
        log.warn("Received unknown model type {}".format(model_event.model_type))
        return None

    def _publish_facts(self, facts):
        ts = time.time()
        if self._zing_connector_client.send_facts(facts):
            elapsed = time.time() - ts
            log.debug("sending {} facts to zing-connector took {} seconds".format(len(facts), elapsed))

    def _device_organizers_changed(self, model_event):
        return model_event.type in ORGANIZER_FACT_MODEL_EVENT_TYPES and \
               model_event.model_type == MODELCONSTANTS.DEVICE

    def _process(self, event):
        ignore_uuids = set(getattr(event, 'maintWindowChanges', []))
        facts = []
        organizers_fact_uuids = set() # uuids for which we need to send an organizers fact
        for model_event in chain(*(i.events for i in event.msgs)):
            if model_event.device.uuid in ignore_uuids:
                continue
            if self._device_organizers_changed(model_event):
                uuid = self._get_uuid(model_event)
                if uuid:
                    organizers_fact_uuids.add(uuid)
        for uuid in organizers_fact_uuids:
            obj = self._get_object(uuid)
            if obj:
                fact = device_organizers_fact(obj)
                facts.append(fact)
            else:
                log.error("Could not get object with uuid {}".format(uuid))
        return facts

    def process(self, event):
        ts = time.time()
        facts = self._process(event)
        if facts:
            self._publish_facts(facts)
            # FIXME set this to debug
            log.info("processing post commit model change event took {} seconds".format(time.time() - ts))


@adapter(IMessagePostPublishingEvent)
def model_change_listener(event):
    log.debug("Processing post commit model change event...")
    try:
        PostCommitModelEventProcessor().process(event)
    except Exception as e:
        log.error("Exception processing after commit model change events: {}".format(e))
