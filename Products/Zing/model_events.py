##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy
import time
import traceback

from zope.component import adapter
from itertools import chain
from logging import getLogger

from Products.ZenMessaging.ChangeEvents.interfaces import IMessagePostPublishingEvent
from Products.Zuul.utils import get_dmd
from Products.Zing.interfaces import IZingConnectorProxy
from Products.Zing.fact import organizer_facts_for_devices
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

    """
    @param fact_gen: generator with the facts to send to zing-connector
    """
    def _publish_facts(self, fact_gen):
        ts = time.time()
        success = self._zing_connector_client.send_fact_generator_in_batches(fact_gen)
        if success:
            elapsed = time.time() - ts
            log.info("sending facts to zing-connector took {} seconds".format(elapsed))
        return success == True

    def _device_organizers_changed(self, model_event):
        return model_event.type in ORGANIZER_FACT_MODEL_EVENT_TYPES and \
               model_event.model_type == MODELCONSTANTS.DEVICE

    """
    @param devices_uuids: uuids of the devices to retrieve
    @return: generator of devices
    """
    def _get_devices(self, devices_uuids):
        for dev_uuid in devices_uuids:
            device = self._get_object(dev_uuid)
            if not device:
                log.error("Could not get object with uuid {}".format(dev_uuid))
                continue
            yield device

    """
    @return: generator of facts
    """
    def _process(self, event):
        fact_generators = []
        ignore_uuids = set(getattr(event, 'maintWindowChanges', []))
        need_organizers_fact = set() # device uuids for which we need to send an organizers fact
        for model_event in chain(*(i.events for i in event.msgs)):
            if model_event.device.uuid in ignore_uuids:
                continue
            if self._device_organizers_changed(model_event):
                uuid = self._get_uuid(model_event)
                if uuid:
                    need_organizers_fact.add(uuid)
        if need_organizers_fact:
            devices_gen = self._get_devices(need_organizers_fact)
            org_facts_gen = organizer_facts_for_devices(devices_gen, include_components=True)
            fact_generators.append(org_facts_gen)
        return chain(*fact_generators)

    def process(self, event):
        ts = time.time()
        facts = self._process(event)
        self._publish_facts(facts)
        # FIXME set this to debug
        log.info("processing post commit model change event took {} seconds".format(time.time() - ts))


@adapter(IMessagePostPublishingEvent)
def model_change_listener(event):
    log.debug("Processing post commit model change event...")
    try:
        PostCommitModelEventProcessor().process(event)
    except Exception as e:
        log.exception(traceback.format_exc())
        log.error("Exception processing after commit model change events: {}".format(e))
