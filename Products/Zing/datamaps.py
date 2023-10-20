##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018-2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from collections import defaultdict
from zope.component import subscribers, adapter
from zope.component.factory import Factory
from zope.interface import implementer

from Products.DataCollector.ApplyDataMap import (
    IDatamapAppliedEvent,
    IncrementalDataMap,
)
from Products.DataCollector.plugins.DataMaps import (
    MultiArgs,
    ObjectMap,
    PLUGIN_NAME_ATTR,
    RelationshipMap,
)

from . import fact as ZFact
from .interfaces import IObjectMapContextProvider, IZingDatamapHandler
from .tx_state import ZingTxStateManager
from .entity_type import get_object_entity_type, get_object_entity_domain, get_object_entity_zenpack

log = logging.getLogger("zen.zing.datamaps")


@adapter(IDatamapAppliedEvent)
def zing_add_datamap(event):
    if event.datamap.target:
        log.debug("zing_add_datamap handling event=%s", event)
        zing_datamap_handler = ZingDatamapHandler(event.datamap._base.dmd)
        zing_datamap_handler.add_context(event.datamap, event.datamap.target)
        zing_datamap_handler.add_datamap(event.datamap.target, event.datamap)
    else:
        log.debug("zing_add_datamap skipped handling of event. Missing 'target': %s", event)
        return


class ObjectMapContext(object):
    def __init__(self, obj):
        self._obj = obj
        self.uuid = None
        self.meta_type = None
        self.name = None
        self.mem_capacity = None
        self.is_device = False
        self.is_device_component = False
        self.dimensions = {}
        self.metadata = {}
        self._extract_relevant_fields(obj)

    def _extract_relevant_fields(self, obj):
        """Extract fields that will be used to construct a fact."""
        try:
            self.uuid = obj.getUUID()
        except Exception:
            pass
        try:
            self.meta_type = obj.meta_type
        except Exception:
            pass
        try:
            self.name = obj.titleOrId()
        except Exception:
            pass

        from Products.ZenModel.Device import Device

        if isinstance(obj, Device):
            self.is_device = True
            try:
                self.mem_capacity = obj.hw.totalMemory
            except Exception:
                pass

        from Products.ZenModel.DeviceComponent import DeviceComponent

        if isinstance(obj, DeviceComponent):
            self.is_device_component = True

        # Get extra context from IObjectMapContextProvider adapters.
        for provider in subscribers([obj], IObjectMapContextProvider):
            try:
                merge_fields(self.dimensions, provider.get_dimensions(obj))
            except Exception as e:
                log.error(
                    "%s failed to get dimensions for %s: %s", provider, obj, e
                )

            try:
                merge_fields(self.metadata, provider.get_metadata(obj))
            except Exception as e:
                log.error(
                    "%s failed to get metadata for %s: %s", provider, obj, e
                )


def merge_fields(d, new):
    """Merge fields from new (dict) into d (dict).

    Top-level list values will be concatenated, and top-level dict
    values will be shallow-merged. All other cases of conflicting keys
    will result in values from ndict overwriting those in odict.

    """
    if not new:
        return

    for k, v in new.iteritems():
        if k not in d:
            d[k] = v
        elif isinstance(v, list) and isinstance(d[k], list):
            d[k].extend(v)
        elif isinstance(v, dict) and isinstance(d[k], dict):
            d[k].update(v)
        else:
            d[k] = v


@implementer(IZingDatamapHandler)
class ZingDatamapHandler(object):

    def __init__(self, context):
        self.context = context
        self.zing_tx_state_manager = ZingTxStateManager()

    def _get_zing_tx_state(self):
        return self.zing_tx_state_manager.get_zing_tx_state(self.context)

    def add_datamap(self, ctx, datamap):
        """Adds the datamap to the ZingDatamapsTxState in the current tx."""
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps.append((ctx.device(), datamap))

    def add_context(self, objmap, ctx):
        """Adds the context to the ZingDatamapsTxState in the current tx."""
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps_contexts[objmap] = ObjectMapContext(ctx)

    def _generate_facts(self, facts_per_device, zing_tx_state):
        """
        Given a dict of device:facts from datamap, it returns a generator that
        includes all the received facts plus some additional facts (organizers
        fact, device info fact and impact relationship fact)
        """
        for device, facts in facts_per_device.iteritems():
            device_organizers_fact = ZFact.organizer_fact_from_device(device)

            for (f, ctx) in facts:

                # Return datamap fact
                comp_uuid = f.metadata.get(
                    ZFact.DimensionKeys.CONTEXT_UUID_KEY, ""
                )
                zing_tx_state.already_generated_device_info_facts.add(
                    comp_uuid
                )
                yield f
                if ctx is None:
                    for component in device.getDeviceComponents():
                        if component.getUUID() == comp_uuid:
                            ctx = ObjectMapContext(component)
                            break
                comp_groups = []
                if ctx is not None and ctx.is_device_component:

                    # organizers and impact relationships facts for the component
                    comp_groups = ctx._obj.getComponentGroupNames()
                    # organizers fact for the component
                if comp_uuid not in zing_tx_state.already_generated_organizer_facts:
                    comp_meta = f.metadata.get(
                        ZFact.DimensionKeys.META_TYPE_KEY, ""
                    )
                    comp_org_fact = ZFact.organizer_fact_from_device_component(
                        device_organizers_fact,
                        comp_uuid,
                        comp_meta,
                        comp_groups,
                    )
                    if comp_org_fact.is_valid():
                        zing_tx_state.already_generated_organizer_facts.add(
                            comp_uuid
                        )
                        yield comp_org_fact
                # impact relationship fact for the component
                comp_impact_fact = ZFact.impact_relationships_fact_if_needed(
                    zing_tx_state, comp_uuid
                )
                if comp_impact_fact:
                    yield comp_impact_fact

            # generate facts for the device
            dev_uuid = device.getUUID()
            if dev_uuid:
                # send organizers fact
                if (
                    dev_uuid
                    not in zing_tx_state.already_generated_organizer_facts
                    and device_organizers_fact.is_valid()
                ):
                    zing_tx_state.already_generated_organizer_facts.add(
                        dev_uuid
                    )
                    yield device_organizers_fact
                # send device info fact
                if (
                    dev_uuid
                    not in zing_tx_state.already_generated_device_info_facts
                ):
                    dev_info_fact = ZFact.device_info_fact(device)
                    if dev_info_fact.is_valid():
                        zing_tx_state.already_generated_device_info_facts.add(
                            dev_uuid
                        )
                        yield dev_info_fact
                # send impact relationships fact
                dev_impact_fact = ZFact.impact_relationships_fact_if_needed(
                    zing_tx_state, dev_uuid
                )
                if dev_impact_fact:
                    yield dev_impact_fact

    def generate_facts(self, zing_tx_state):
        """
        @return: Fact generator
        """
        log.debug(
            "Processing %s datamaps to send to zing-connector.",
            len(zing_tx_state.datamaps),
        )
        facts_per_device = defaultdict(list)
        for device, datamap in zing_tx_state.datamaps:
            dm_facts = self.facts_from_datamap(
                device, datamap, zing_tx_state.datamaps_contexts
            )
            if dm_facts:
                facts_per_device[device].extend(dm_facts)
        return self._generate_facts(facts_per_device, zing_tx_state)

    def fact_from_object_map(
        self,
        om,
        parent_device=None,
        relationship=None,
        contexts=None,
        dm_plugin=None,
    ):
        om_context = (contexts or {}).get(om)
        if om_context is not None:
            f = ZFact.device_info_fact(om_context._obj)
            parent_device = om_context._obj.device()
            if relationship is not None:
                f.metadata[ZFact.DimensionKeys.RELATION_KEY] = relationship
            else:
                f.metadata[
                    ZFact.DimensionKeys.RELATION_KEY
                ] = om_context._obj.getPrimaryParent().id
            try:
                parent = om_context._obj.getPrimaryParent().getPrimaryParent()
                if parent.id in ("os", "hw"):
                    parent = parent_device
                f.metadata[ZFact.DimensionKeys.PARENT_KEY] = parent.getUUID()
            except Exception:
                pass
        else:
            f = ZFact.Fact()
        d = om.__dict__.copy()
        if "_attrs" in d:
            del d["_attrs"]
        if "classname" in d and not d["classname"]:
            del d["classname"]
        for k, v in d.items():
            # These types are currently all that the model ingest service
            # can handle.
            if not isinstance(
                v, (str, int, long, float, bool, list, tuple, MultiArgs, set)
            ):
                del d[k]
            elif isinstance(v, MultiArgs):
                d[k] = v.args
        f.update(d)

        if parent_device is not None:
            f.data[
                ZFact.MetadataKeys.DEVICE_UUID_KEY
            ] = parent_device.getUUID()
            f.data[ZFact.MetadataKeys.DEVICE_KEY] = parent_device.id

        plugin_name = getattr(om, PLUGIN_NAME_ATTR, None) or dm_plugin
        if plugin_name:
            f.metadata[ZFact.DimensionKeys.PLUGIN_KEY] = plugin_name

        # Hack in whatever extra stuff we need.
        if om_context is not None:
            self.apply_extra_fields(om_context, f)

        # FIXME temp solution until we are sure all zenpacks send the plugin
        if not f.metadata.get(ZFact.DimensionKeys.PLUGIN_KEY):
            log.warn("Found fact without plugin information: %s", f.metadata)
            if f.metadata.get(ZFact.DimensionKeys.META_TYPE_KEY):
                f.metadata[ZFact.DimensionKeys.PLUGIN_KEY] = f.metadata[
                    ZFact.DimensionKeys.META_TYPE_KEY
                ]
        return f, om_context

    def fact_from_incremental_map(self, idm, contexts=None):
        parent_device = None
        parent = idm.parent
        relname = idm.relname
        om_context = (contexts or {}).get(idm)
        if om_context is not None:
            f = ZFact.device_info_fact(om_context._obj)
            parent_device = om_context._obj.device()
            if not parent or parent == om_context._obj:
                parent = om_context._obj.getPrimaryParent().getPrimaryParent()
            if not relname:
                relname = om_context._obj.getPrimaryParent().id
        else:
            f = ZFact.Fact()
        valid_types = (
            str,
            int,
            long,
            float,
            bool,
            list,
            tuple,
            MultiArgs,
            set,
        )

        objectmap = {k: v for k, v in idm.iteritems()}
        for k, v in objectmap.items():
            # These types are currently all that the model ingest service
            # can handle.
            if not isinstance(v, valid_types):
                del objectmap[k]
            elif isinstance(v, MultiArgs):
                objectmap[k] = v.args

        if idm.id:
            objectmap["id"] = idm.id
        f.update(objectmap)

        if relname:
            f.metadata[ZFact.DimensionKeys.RELATION_KEY] = relname
        try:
            if parent:
                parent_device = parent_device or parent.device()
                if parent.id in ("os", "hw"):
                    parent = parent_device
                f.metadata[ZFact.DimensionKeys.PARENT_KEY] = parent.getUUID()
                f.data[ZFact.MetadataKeys.DEVICE_UUID_KEY] = parent_device.getUUID()
                f.data[ZFact.MetadataKeys.DEVICE_KEY] = parent_device.id
        except Exception:
            log.debug("parent UUID not found")

        # Hack in whatever extra stuff we need.
        if om_context is not None:
            self.apply_extra_fields(om_context, f)

        if getattr(idm, PLUGIN_NAME_ATTR, None):
            f.metadata[ZFact.DimensionKeys.PLUGIN_KEY] = idm.plugin_name

        # FIXME temp solution until we are sure all zenpacks send the plugin
        if not f.metadata.get(ZFact.DimensionKeys.PLUGIN_KEY):
            log.warn("Found fact without plugin information: %s", f.metadata)
            if f.metadata.get(ZFact.DimensionKeys.META_TYPE_KEY):
                f.metadata[ZFact.DimensionKeys.PLUGIN_KEY] = f.metadata[
                    ZFact.DimensionKeys.META_TYPE_KEY
                ]

        if idm.directive == "remove":
            log.info(
                "Generated fact from a 'remove' incremental datamap  "
                "directive=%s target=%s fact-id=%s",
                idm.directive, idm.target, f.id,
            )
        return f, om_context

    def facts_from_datamap(self, device, dm, contexts):
        facts = []
        dm_plugin = getattr(dm, PLUGIN_NAME_ATTR, None)
        if isinstance(dm, RelationshipMap):
            for om in dm.maps:
                (f, ctx) = self.fact_from_object_map(
                    om,
                    device,
                    dm.relname,
                    contexts=contexts,
                    dm_plugin=dm_plugin,
                )
                if f.is_valid():
                    facts.append((f, ctx))
        elif isinstance(dm, ObjectMap):
            (f, ctx) = self.fact_from_object_map(
                dm, contexts=contexts, dm_plugin=dm_plugin
            )
            if f.is_valid():
                facts.append((f, ctx))
        elif isinstance(dm, IncrementalDataMap):
            (f, ctx) = self.fact_from_incremental_map(dm, contexts=contexts)
            if f.is_valid():
                facts.append((f, ctx))
        else:
            log.error("datamap type not found. type=%s", type(dm))
        return facts

    def apply_extra_fields(self, om_context, f):
        """Add information from the ObjectMap context to the fact.

        This is where dimensions and metadata from IObjectMapContextProvider
        adapters are added to facts.

        """
        if om_context.is_device_component:
            f.data[ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY] = "DeviceComponent"
        elif om_context.is_device:
            f.data[ZFact.MetadataKeys.ZEN_SCHEMA_TAGS_KEY] = "Device"
            if om_context.mem_capacity is not None:
                f.data[
                    ZFact.MetadataKeys.MEM_CAPACITY_KEY
                ] = om_context.mem_capacity

        if om_context.dimensions:
            f.metadata.update(om_context.dimensions)

        if om_context.metadata:
            f.data.update(om_context.metadata)

        if om_context.is_device_component or om_context.is_device:
            zenpack = get_object_entity_zenpack(om_context._obj)
            domain = get_object_entity_domain(om_context._obj)
            entity_type = get_object_entity_type(om_context._obj)
            if zenpack is not None:
                f.data[ZFact.MetadataKeys.CZ_ENTITY_ZENPACK_KEY] = entity_type
            if domain is not None:
                f.data[ZFact.MetadataKeys.CZ_ENTITY_DOMAIN_KEY] = entity_type
            if entity_type is not None:
                f.data[ZFact.MetadataKeys.CZ_ENTITY_TYPE_KEY] = entity_type

DATAMAP_HANDLER_FACTORY = Factory(ZingDatamapHandler)
