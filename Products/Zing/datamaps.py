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

from .interfaces import IZingConnectorProxy, IZingDatamapHandler
from .fact import Fact, FactKeys

from zope.interface import implements
from zope.component.factory import Factory

from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap, MultiArgs, PLUGIN_NAME_ATTR

logging.basicConfig()
log = logging.getLogger("zen.zing")


TX_DATA_FIELD_NAME = "zing_datamaps_state"

class ObjectMapContext(object):
    def __init__(self, obj):
        self.uuid = None
        self.meta_type = None
        self.name = None
        self.mem_capacity = None
        self.location = None
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
            try:
                loc = obj.location()
            except Exception:
                pass
            else:
                if loc is not None:
                    self.location = loc.titleOrId()


class ZingDatamapsTxState(object):
    """
    All datamaps processed within a transaction are buffered in this data structure
    in the transaction object. Once the tx successfully commits, datamaps will be
    serialized and sent to zing-connector
    """
    def __init__(self):
        self.datamaps = []
        self.contexts = {}
        self.devices_fact = {} # dummy fact per processed device


class ZingDatamapHandler(object):
    implements(IZingDatamapHandler)

    def __init__(self, context):
        self.context = context
        self.zing_connector = IZingConnectorProxy(context)

    def _get_zing_tx_state(self):
        """
        Get the ZingDatamapsTxState object for the current transaction.
        If it doesnt exists, create it.
        """
        zing_tx_state = None
        current_tx = transaction.get()
        zing_tx_state = getattr(current_tx, TX_DATA_FIELD_NAME, None)
        if not zing_tx_state:
            zing_tx_state = ZingDatamapsTxState()
            setattr(current_tx, TX_DATA_FIELD_NAME, zing_tx_state)
            current_tx.addAfterCommitHook(self.process_datamaps, args=(zing_tx_state,))
            log.info("ZingDatamapHandler AfterCommitHook added. State added to current transaction.")
        return zing_tx_state

    def add_datamap(self, device, datamap):
        """ adds the datamap to the ZingDatamapsTxState in the current tx"""
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps.append( (device, datamap) )
        # Create a dummy fact for the device to make sure Zing has one for each device
        device_uid = device.getPrimaryId()
        if device_uid not in zing_state.devices_fact:
            zing_state.devices_fact[device_uid] = self.fact_from_device(device)

    def add_context(self, objmap, ctx):
        """ adds the context to the ZingDatamapsTxState in the current tx """
        zing_state = self._get_zing_tx_state()
        zing_state.contexts[objmap] = ObjectMapContext(ctx)

    def process_datamaps(self, tx_success, zing_state):
        """
        This is called on the AfterCommitHook
        Send the datamaps to zing-connector if the tx succeeded
        """
        if not tx_success:
            return
        try:
            log.debug("Sending {} datamaps to zing-connector.".format(len(zing_state.datamaps)))
            if not self.zing_connector.ping():
                log.error("Datamaps not forwarded to Zing: zing-connector cant be reached")
                return
            facts = []
            for device, datamap in zing_state.datamaps:
                dm_facts = self.facts_from_datamap(device, datamap, zing_state.contexts)
                if dm_facts:
                    facts.extend(dm_facts)
            # add dummy facts for the processed devices
            device_facts = zing_state.devices_fact.values()
            if device_facts:
                facts.extend(device_facts)
            self._send_facts_in_batches(facts)
        except Exception as ex:
            log.warn("Exception sending datamaps to zing-connector. {}".format(ex))

    def _send_facts_in_batches(self, facts, batch_size=500):
        log.info("Sending {} facts to zing-connector.".format(len(facts)))
        while facts:
            batch = facts[:batch_size]
            del facts[:batch_size]
            self.zing_connector.send_facts(batch)

    def fact_from_device(self, device):
        f = Fact()
        ctx = ObjectMapContext(device)
        f.metadata[FactKeys.CONTEXT_UUID_KEY] = ctx.uuid
        f.metadata[FactKeys.META_TYPE_KEY] = ctx.meta_type
        f.data[FactKeys.NAME_KEY] = ctx.name
        return f

    def fact_from_object_map(self, om, parent_device=None, relationship=None, context=None):
        f = Fact()
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
        plugin_name = getattr(om, PLUGIN_NAME_ATTR, None)
        if plugin_name:
            f.metadata[FactKeys.PLUGIN_KEY] = plugin_name

        # Hack in whatever extra stuff we need.
        om_context = (context or {}).get(om)
        if om_context is not None:
            self.apply_extra_fields(om_context, f)
        return f

    def facts_from_datamap(self, device, dm, context):
        facts = []
        if isinstance(dm, RelationshipMap):
            for om in dm.maps:
                f = self.fact_from_object_map(om, device, dm.relname, context=context)
                if not getattr(om, PLUGIN_NAME_ATTR, None) and \
                    getattr(dm, PLUGIN_NAME_ATTR, None):
                    f.metadata[FactKeys.PLUGIN_KEY] = getattr(dm, PLUGIN_NAME_ATTR)
                if f.is_valid():
                    facts.append(f)
        elif isinstance(dm, ObjectMap):
            f = self.fact_from_object_map(dm, context=context)
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
        fact.metadata[FactKeys.CONTEXT_UUID_KEY] = om_context.uuid
        fact.metadata[FactKeys.META_TYPE_KEY] = om_context.meta_type
        fact.data[FactKeys.NAME_KEY] = om_context.name

        if om_context.is_device:
            if om_context.mem_capacity is not None:
                fact.data[FactKeys.MEM_CAPACITY_KEY] = om_context.mem_capacity
            if FactKeys.LOCATION_KEY not in fact.data and om_context.location is not None:
                fact.data[FactKeys.LOCATION_KEY] = om_context.location

DATAMAP_HANDLER_FACTORY = Factory(ZingDatamapHandler)
