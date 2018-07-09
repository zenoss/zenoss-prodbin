##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time
import traceback
import transaction

from .tx_state import ZingTxStateManager

from zope.component import adapter
from zope.interface import implements

from itertools import chain
from logging import getLogger

from zope.component.factory import Factory

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent

from Products.Zing.interfaces import IZingConnectorProxy
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.Zing.interfaces import IZingObjectUpdateHandler

from Products.Zing import fact

log = getLogger("zen.zing.events")


class ZingObjectUpdateHandler(object):
    implements(IZingObjectUpdateHandler)

    def __init__(self, context):
        self.context = context
        self.zing_tx_state_manager = ZingTxStateManager()
        self.guid_manager = IGUIDManager(self.context)

    def is_object_relevant(self, obj):
        # devices and components with an uuid are relevant
        uuid = None
        try:
            uuid = obj.getUUID()
        except Exception:
            pass
        return uuid and (isinstance(obj, Device) or isinstance(obj, DeviceComponent))

    def _get_zing_tx_state(self):
        """ """
        return self.zing_tx_state_manager.get_zing_tx_state(self.context)

    def _update_object(self, obj, idxs=None):
        if self.is_object_relevant(obj) and isinstance(obj, Device) and idxs:
            # set this to debug
            log.info("buffering object update")
            tx_state = self._get_zing_tx_state()
            uuid = obj.getUUID()
            if "path" in idxs:
                tx_state.need_organizers_fact.add(uuid)
                # we also need to generate organizers facts for all the device components
            if "name" in idxs or "productionState" in idxs:
                tx_state.need_device_info_fact.add(uuid)
            tx_state.need_deletion_fact.discard(uuid)

    def _delete_object(self, obj):
        if self.is_object_relevant(obj):
            # set this to debug
            log.info("buffering object deletion")
            uuid = obj.getUUID()
            tx_state = self._get_zing_tx_state()
            tx_state.need_deletion_fact.add(uuid)
            tx_state.need_organizers_fact.discard(uuid)
            tx_state.need_device_info_fact.discard(uuid)

    def update_object(self, obj, idxs=None):
        """
        ModelCatalog calls this method when it determines that an object has been updated
        """
        try:
            self._update_object(obj, idxs)
        except Exception as ex:
            log.exception(traceback.format_exc())
            log.error("Exception buffering object update for Zing. {}".format(ex))

    def delete_object(self, obj):
        """
        ModelCatalog calls this method when it determines that an object has been deleted
        """
        try:
            self._delete_object(obj)
        except Exception as ex:
            log.exception(traceback.format_exc())
            log.error("Exception buffering object deletion for Zing. {}".format(ex))

    def _generate_device_info_facts(self, uuids, tx_state):
        for uuid in uuids:
            if uuid in tx_state.already_generated_device_info_facts:
                continue
            obj = self.guid_manager.getObject(uuid)
            if obj:
                f = fact.device_info_fact(obj)
                if f.is_valid():
                    tx_state.already_generated_device_info_facts.add(uuid)
                    yield f

    def _generate_deletion_facts(self, uuids, tx_state):
        for uuid in uuids:
            f = fact.deletion_fact(uuid)
            if f.is_valid():
                yield f

    def _generate_organizers_facts(self, uuids, tx_state):
        for uuid in uuids: # all the uuids are devices ( see self.update_object )
            device = self.guid_manager.getObject(uuid)
            if device:
                device_fact = fact.organizer_fact_from_device(device)
                if uuid not in tx_state.already_generated_organizer_facts and device_fact.is_valid():
                    yield device_fact
                # send an organizers fact for each component
                for comp_brain in device.componentSearch(query={}):
                    if not comp_brain.getUUID or \
                       comp_brain.getUUID in tx_state.already_generated_organizer_facts:
                        continue
                    comp_fact = fact.organizer_fact_from_device_component(device_fact, comp_brain.getUUID, comp_brain.meta_type)
                    if comp_fact.is_valid():
                        tx_state.already_generated_organizer_facts.add(comp_brain.getUUID)
                        yield comp_fact

    def generate_facts(self, tx_state):
        """
        @return: Fact generator
        """
        # TODO set this to debug
        log.info("Processing {} device info facts".format(tx_state.need_device_info_fact))
        log.info("Processing {} organizers facts".format(tx_state.need_organizers_fact))
        log.info("Processing {} deletion facts".format(tx_state.need_deletion_fact))
        dev_info_uuids = tx_state.need_device_info_fact - tx_state.already_generated_device_info_facts
        orgs_uuids = tx_state.need_organizers_fact - tx_state.already_generated_organizer_facts
        fact_generators = []
        fact_generators.append(self._generate_device_info_facts(dev_info_uuids, tx_state))
        fact_generators.append(self._generate_organizers_facts(orgs_uuids, tx_state))
        fact_generators.append(self._generate_deletion_facts(tx_state.need_deletion_fact, tx_state))
        return chain(*fact_generators)


OBJECT_UPDATE_HANDLER_FACTORY = Factory(ZingObjectUpdateHandler)

