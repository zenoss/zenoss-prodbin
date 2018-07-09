##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging
import transaction
import traceback
from collections import defaultdict

from Products.Zing import fact

from Products.Zing.interfaces import IZingDatamapHandler
from Products.Zing.tx_state import ZingTxStateManager

from zope.interface import implements
from zope.component.factory import Factory

from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap, MultiArgs, PLUGIN_NAME_ATTR

logging.basicConfig()
log = logging.getLogger("zen.zing.datamaps")


class ObjectMapContext(object):
    def __init__(self, obj):
        self.uuid = None
        self.meta_type = None
        self.name = None
        self.mem_capacity = None
        self.is_device = False
        self._extract_relevant_fields(obj)

    def _extract_relevant_fields(self, obj):
        try:
            self.uuid = obj.getUUID()
        except:
            pass
        try:
            self.meta_type = obj.meta_type
        except:
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


class ZingDatamapHandler(object):
    implements(IZingDatamapHandler)

    def __init__(self, context):
        self.context = context
        self.zing_tx_state_manager = ZingTxStateManager()

    def _get_zing_tx_state(self):
        """ """
        return self.zing_tx_state_manager.get_zing_tx_state(self.context)

    def add_datamap(self, device, datamap):
        """ adds the datamap to the ZingDatamapsTxState in the current tx"""
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps.append( (device, datamap) )

    def add_context(self, objmap, ctx):
        """ adds the context to the ZingDatamapsTxState in the current tx """
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps_contexts[objmap] = ObjectMapContext(ctx)

    """
    Given a dict of device:facts from datamap, it returns a generator that includes
    all the received facts plus the organizers fact for each of the received facts
    """
    def _generate_facts(self, facts_per_device, zing_tx_state):
        generated_organizer_facts = zing_tx_state.already_generated_organizer_facts
        for device, facts in facts_per_device.iteritems():
            device_organizers_fact = fact.organizer_fact_from_device(device)
            for fact in facts:
                yield fact
                comp_uuid = fact.metadata.get(fact.FactKeys.CONTEXT_UUID_KEY, "")
                if comp_uuid not in generated_organizer_facts:
                    comp_meta = fact.metadata.get(fact.FactKeys.META_TYPE_KEY, "")
                    comp_fact = fact.organizer_fact_from_device_component(device_organizers_fact, comp_uuid, comp_meta)
                    if comp_fact.is_valid():
                        generated_organizer_facts.add(comp_uuid)
                        yield comp_fact
                else:
                    log.info("PACOOO SAVED ONE UPDATE")
            dev_uuid = device.getUUID()
            # send organizers fact for the device
            if dev_uuid not in zing_tx_state.already_generated_organizer_facts and device_organizers_fact.is_valid():
                zing_tx_state.already_generated_organizer_facts.add(dev_uuid)
                yield device_organizers_fact
            else:
                log.info("PACOOO SAVED ONE ORGANIZERS FACT UPDATE")
            # send device info fact
            dev_info_fact = fact.device_info_fact(device)
            if dev_uuid not in zing_tx_state.already_generated_device_info_facts and dev_info_fact.is_valid():
                zing_tx_state.already_generated_device_info_facts.add(dev_uuid)
                yield dev_info_fact
            else:
                log.info("PACOOO SAVED ONE DEVICE INFO UPDATE")

    def generate_facts(self, zing_tx_state):
        """
        @return: Fact generator
        """
        log.debug("Processing {} datamaps to send to zing-connector.".format(len(zing_tx_state.datamaps)))
        facts_per_device = defaultdict(list)
        for device, datamap in zing_tx_state.datamaps:
            dm_facts = self.facts_from_datamap(device, datamap, zing_tx_state.datamaps_contexts)
            if dm_facts:
                facts_per_device[device].extend(dm_facts)
        return self._generate_facts(facts_per_device, zing_tx_state)

    def fact_from_device(self, device):
        f = fact.Fact()
        ctx = ObjectMapContext(device)
        f.metadata[fact.FactKeys.CONTEXT_UUID_KEY] = ctx.uuid
        f.metadata[fact.FactKeys.META_TYPE_KEY] = ctx.meta_type
        f.metadata[fact.FactKeys.PLUGIN_KEY] = ctx.meta_type
        f.data[fact.FactKeys.NAME_KEY] = ctx.name
        return f

    def fact_from_object_map(self, om, parent_device=None, relationship=None, context=None, dm_plugin=None):
        f = fact.Fact()
        d = om.__dict__.copy()
        if "_attrs" in d:
            del d["_attrs"]
        if "classname" in d and not d["classname"]:
            del d["classname"]
        for k, v  in d.items():
            # These types are currently all that the model ingest service can handle.
            if not isinstance(v, (str, int, long, float, bool, list, tuple, MultiArgs, set)):
                del d[k]
            elif isinstance(v, MultiArgs):
                d[k] = v.args
        f.update(d)
        if parent_device is not None:
            f.metadata["parent"] = parent_device.getUUID()
        if relationship is not None:
            f.metadata["relationship"] = relationship
        plugin_name = getattr(om, PLUGIN_NAME_ATTR, None) or dm_plugin
        if plugin_name:
            f.metadata[fact.FactKeys.PLUGIN_KEY] = plugin_name

        # Hack in whatever extra stuff we need.
        om_context = (context or {}).get(om)
        if om_context is not None:
            self.apply_extra_fields(om_context, f)

        # FIXME temp solution until we are sure all zenpacks send the plugin
        if not f.metadata.get(fact.FactKeys.PLUGIN_KEY):
            log.warn("Found fact without plugin information: {}".format(f.metadata))
            if f.metadata.get(fact.FactKeys.META_TYPE_KEY):
                f.metadata[fact.FactKeys.PLUGIN_KEY] = f.metadata[fact.FactKeys.META_TYPE_KEY]
        return f

    def facts_from_datamap(self, device, dm, context):
        facts = []
        dm_plugin = getattr(dm, PLUGIN_NAME_ATTR, None)
        if isinstance(dm, RelationshipMap):
            for om in dm.maps:
                f = self.fact_from_object_map(om, device, dm.relname, context=context, dm_plugin=dm_plugin)
                if f.is_valid():
                    facts.append(f)
        elif isinstance(dm, ObjectMap):
            f = self.fact_from_object_map(dm, context=context, dm_plugin=dm_plugin)
            if f.is_valid():
                facts.append(f)
        return facts

    def apply_extra_fields(self, om_context, fact):
        """
        A simple (temporary) hook to add extra information to a fact that isn't
        found in the datamap that triggered this serialization. This needs a proper
        event subscriber framework to be maintainable, so this will only work so
        long as the number of fields is pretty small.
        """
        fact.metadata[fact.FactKeys.CONTEXT_UUID_KEY] = om_context.uuid
        fact.metadata[fact.FactKeys.META_TYPE_KEY] = om_context.meta_type
        fact.data[fact.FactKeys.NAME_KEY] = om_context.name

        if om_context.is_device:
            if om_context.mem_capacity is not None:
                fact.data[fact.FactKeys.MEM_CAPACITY_KEY] = om_context.mem_capacity

DATAMAP_HANDLER_FACTORY = Factory(ZingDatamapHandler)
