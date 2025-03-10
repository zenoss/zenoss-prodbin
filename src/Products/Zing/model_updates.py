##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from itertools import chain
from logging import getLogger

from zope.component.factory import Factory
from zope.interface import implementer

from Products.ZenModel.ComponentGroup import ComponentGroup
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer

from . import fact as ZFact
from .interfaces import IZingObjectUpdateHandler
from .tx_state import ZingTxStateManager

log = getLogger("zen.zing.model_updates")


@implementer(IZingObjectUpdateHandler)
class ZingObjectUpdateHandler(object):
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
        return uuid and isinstance(
            obj, (ComponentGroup, Device, DeviceComponent, DeviceOrganizer,)
        )

    def _get_zing_tx_state(self):
        return self.zing_tx_state_manager.get_zing_tx_state(self.context)

    def _update_object(self, obj, idxs=None):
        tx_state = self._get_zing_tx_state()
        uuid = obj.getUUID()
        tx_state.need_deletion_fact.pop(uuid, None)
        log.debug("buffering object update for %s", uuid)

        if isinstance(obj, Device):
            parent = obj.getPrimaryParent().getPrimaryParent()

            device_fact = ZFact.device_info_fact(obj)
            device_fact.metadata.update(
                {
                    ZFact.DimensionKeys.PARENT_KEY: parent.getUUID(),
                    ZFact.DimensionKeys.RELATION_KEY:
                        obj.getPrimaryParent().id,
                    ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY: "Device",
                }
            )
            tx_state.need_device_info_fact[uuid] = device_fact


            if idxs and "path" in idxs:
                
                device_org_fact = ZFact.organizer_fact_from_device(obj)
                tx_state.need_organizers_fact[uuid] = device_org_fact

                # If the device's organizers were changed, we also need to
                # generate updated organizer facts for all of the device's
                # components
                for comp_brain in obj.componentSearch(query={}):
                    if not comp_brain.getUUID:
                        continue
                    try:
                        comp_org_fact = ZFact.organizer_fact_without_groups_from_device_component(
                            device_org_fact,
                            comp_brain.getUUID,
                            comp_brain.meta_type,
                        )
                        tx_state.need_organizers_fact[
                            comp_brain.getUUID
                        ] = comp_org_fact
                    except Exception:
                        log.exception(
                            "Cannot find object at path %s",
                            comp_brain.getPath()
                        )

        elif isinstance(obj, DeviceComponent):
            parent = obj.getPrimaryParent().getPrimaryParent()
            if parent.id in ("os", "hw"):
                parent = parent.device()

            comp_fact = ZFact.device_info_fact(obj)
            comp_fact.metadata.update(
                {
                    ZFact.DimensionKeys.PARENT_KEY: parent.getUUID(),
                    ZFact.DimensionKeys.RELATION_KEY:
                        obj.getPrimaryParent().id,
                    ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY: "DeviceComponent",
                }
            )
            tx_state.need_device_info_fact[uuid] = comp_fact

            device_org_fact = ZFact.organizer_fact_from_device(obj.device())
            comp_org_fact = ZFact.organizer_fact_from_device_component(
                device_org_fact,
                uuid,
                obj.meta_type,
                obj.getComponentGroupNames(),
            )
            tx_state.need_organizers_fact[uuid] = comp_org_fact

        elif isinstance(obj, DeviceOrganizer):
            org_fact = ZFact.device_organizer_info_fact(obj)
            tx_state.need_device_organizer_info_fact[uuid] = org_fact

        elif isinstance(obj, ComponentGroup):
            cgroup_fact = ZFact.component_group_info_fact(obj)
            tx_state.need_component_group_info_fact[uuid] = cgroup_fact

    def _delete_object(self, obj):
        if self.is_object_relevant(obj):
            uuid = obj.getUUID()
            log.debug("buffering object deletion for %s", uuid)
            tx_state = self._get_zing_tx_state()
            f = ZFact.deletion_fact(uuid)
            tx_state.need_deletion_fact[uuid] = f

    def update_object(self, obj, idxs=None):
        """
        ModelCatalog calls this method when an object needs to be updated
        """
        try:
            if not self.is_object_relevant(obj):
                return

            self._update_object(obj, idxs)
        except Exception:
            log.exception("Exception buffering object update for Zing")

    def delete_object(self, obj):
        """
        ModelCatalog calls this method when an object needs to be deleted
        """
        try:
            self._delete_object(obj)
        except Exception:
            log.exception("Exception buffering object deletion for Zing")

    def _generate_facts(
        self, uuid_to_fact, already_generated=None, tx_state=None
    ):
        """
        :param uuid_to_fact: dict uuid: Fact
        :param already_generated: uuids that already have a generated fact
        :return: Fact generator
        """
        if already_generated is None:
            already_generated = set()  # always track uuid facts.
        for uuid, fact in uuid_to_fact.iteritems():
            if uuid in already_generated:
                continue
            if not fact.is_valid():
                continue
            already_generated.add(uuid)
            if tx_state is not None:
                impact_fact = ZFact.impact_relationships_fact_if_needed(
                    tx_state, uuid
                )
                if impact_fact:
                    yield impact_fact
            yield fact
            if ZFact.MetadataKeys.DELETED_KEY in fact.data:
                log.info(
                    "Generated a delete fact  uuid=%s fact-id=%s",
                    uuid, fact.id,
                )

    def generate_facts(self, tx_state):
        """
        @return: Fact generator
        """
        fact_generators = []
        if tx_state.need_device_info_fact:
            # TODO set this to debug
            log.info(
                "Processing %s device info updates",
                len(tx_state.need_device_info_fact),
            )
            fact_generators.append(
                self._generate_facts(
                    tx_state.need_device_info_fact,
                    tx_state.already_generated_device_info_facts,
                    tx_state,
                )
            )
        if tx_state.need_device_organizer_info_fact:
            # TODO set this to debug
            log.info(
                "Processing %s device organizer info updates",
                len(tx_state.need_device_organizer_info_fact),
            )
            fact_generators.append(
                self._generate_facts(
                    tx_state.need_device_organizer_info_fact,
                    tx_state.already_generated_device_organizer_info_facts,
                    tx_state,
                )
            )
        if tx_state.need_component_group_info_fact:
            # TODO set this to debug
            log.info(
                "Processing %s component group info updates",
                len(tx_state.need_component_group_info_fact),
            )
            fact_generators.append(
                self._generate_facts(
                    tx_state.need_component_group_info_fact,
                    tx_state.already_generated_component_group_info_facts,
                    tx_state,
                )
            )
        if tx_state.need_organizers_fact:
            # TODO set this to debug
            log.info(
                "Processing %s organizers updates",
                len(tx_state.need_organizers_fact),
            )
            fact_generators.append(
                self._generate_facts(
                    tx_state.need_organizers_fact,
                    tx_state.already_generated_organizer_facts,
                )
            )
        if tx_state.need_deletion_fact:
            # TODO set this to debug
            log.info(
                "Processing %s deletion updates",
                len(tx_state.need_deletion_fact),
            )
            fact_generators.append(
                self._generate_facts(tx_state.need_deletion_fact)
            )
        return chain(*fact_generators)


OBJECT_UPDATE_HANDLER_FACTORY = Factory(ZingObjectUpdateHandler)
