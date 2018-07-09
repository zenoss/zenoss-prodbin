##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import traceback

from itertools import chain
from logging import getLogger

from zope.component.factory import Factory
from zope.interface import implements

from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.Zing import fact as ZFact
from Products.Zing.interfaces import IZingObjectUpdateHandler
from Products.Zing.tx_state import ZingTxStateManager


log = getLogger("zen.zing.model_updates")


class ZingObjectUpdateHandler(object):
    implements(IZingObjectUpdateHandler)

    def __init__(self, context):
        self.context = context.getDmd()
        self.zing_tx_state_manager = ZingTxStateManager()

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
        if self.is_object_relevant(obj) and isinstance(obj, Device):
            tx_state = self._get_zing_tx_state()
            uuid = obj.getUUID()
            tx_state.need_deletion_fact.pop(uuid, None)
            if idxs:
                # set this to debug
                log.debug("buffering object update for {}".format(uuid))
                if "path" in idxs:
                    device_fact = ZFact.organizer_fact_from_device(obj)
                    tx_state.need_organizers_fact[uuid] = device_fact
                    # we also need to generate organizers facts for all the device components
                    for comp_brain in obj.componentSearch(query={}):
                        if not comp_brain.getUUID:
                            continue
                        comp_fact = ZFact.organizer_fact_from_device_component(device_fact, comp_brain.getUUID, comp_brain.meta_type)
                        tx_state.need_organizers_fact[comp_brain.getUUID] = comp_fact
                if "name" in idxs or "productionState" in idxs:
                    tx_state.need_device_info_fact[uuid] = ZFact.device_info_fact(obj)

    def _delete_object(self, obj):
        if self.is_object_relevant(obj):
            uuid = obj.getUUID()
            log.debug("buffering object deletion for {}".format(uuid))
            tx_state = self._get_zing_tx_state()
            tx_state.need_deletion_fact[uuid] = ZFact.deletion_fact(uuid)

    def update_object(self, obj, idxs=None):
        """
        ModelCatalog calls this method when an object needs to be updated
        """
        try:
            self._update_object(obj, idxs)
        except Exception as ex:
            log.exception(traceback.format_exc())
            log.error("Exception buffering object update for Zing. {}".format(ex))

    def delete_object(self, obj):
        """
        ModelCatalog calls this method when an object needs to be deleted
        """
        try:
            self._delete_object(obj)
        except Exception as ex:
            log.exception(traceback.format_exc())
            log.error("Exception buffering object deletion for Zing. {}".format(ex))

    def _generate_facts(self, uuid_to_fact, already_generated=None):
        """
        :param uuid_to_fact: dict uuid: Fact
        :param already_generated: uuids for which we have already generated a fact
        :return: Fact generator
        """
        for uuid, fact in uuid_to_fact.iteritems():
            if already_generated and uuid in already_generated:
                continue
            if fact.is_valid():
                if already_generated:
                    already_generated.add(uuid)
                yield fact

    def generate_facts(self, tx_state):
        """
        @return: Fact generator
        """
        fact_generators = []
        if tx_state.need_device_info_fact:
            # TODO set this to debug
            log.info("Processing {} device info updates".format(len(tx_state.need_device_info_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_device_info_fact,
                                   tx_state.already_generated_device_info_facts))
        if tx_state.need_organizers_fact:
            # TODO set this to debug
            log.info("Processing {} organizers updates".format(len(tx_state.need_organizers_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_organizers_fact,
                                   tx_state.already_generated_organizer_facts))
        if tx_state.need_deletion_fact:
            # TODO set this to debug
            log.info("Processing {} deletion updates".format(len(tx_state.need_deletion_fact)))
            fact_generators.append(self._generate_facts(tx_state.need_deletion_fact))
        return chain(*fact_generators)


OBJECT_UPDATE_HANDLER_FACTORY = Factory(ZingObjectUpdateHandler)

