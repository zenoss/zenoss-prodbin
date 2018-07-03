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
from itertools import chain

from .interfaces import IZingConnectorProxy, IZingDatamapHandler
from .fact import Fact, FactKeys, organizer_facts_for_devices

from zope.interface import implements
from zope.component.factory import Factory

from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap, MultiArgs, PLUGIN_NAME_ATTR

logging.basicConfig()
log = logging.getLogger("zen.zing.datamaps")


TX_DATA_FIELD_NAME = "zing_datamaps_state"


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


class ZingDatamapsTxState(object):
    """
    All datamaps processed within a transaction are buffered in this data structure
    in the transaction object. Once the tx successfully commits, datamaps will be
    serialized and sent to zing-connector
    """
    def __init__(self):
        self.datamaps = []
        self.contexts = {}
        # for each processed device, we store its path to be able to generate additional facts
        self.processed_devices = set()


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
            log.debug("ZingDatamapHandler AfterCommitHook added. State added to current transaction.")
        return zing_tx_state

    def add_datamap(self, device, datamap):
        """ adds the datamap to the ZingDatamapsTxState in the current tx"""
        zing_state = self._get_zing_tx_state()
        zing_state.datamaps.append( (device, datamap) )
        # store the device path so we can create additional facts later
        zing_state.processed_devices.add(device.getPrimaryId())

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
            gen_list = [ (f for f in facts) ]
            # for each processed device and its components, generate a zen_organizers fact
            devices = ( self.context.unrestrictedTraverse(device_uid, None) for device_uid in zing_state.processed_devices )
            # FIXME for devices with incremental modeling, this is sending the organizers fact for the device
            # over and over. Also, we are not sending organizers fact for components
            gen_list.append(organizer_facts_for_devices(devices, include_components=False))
            self.zing_connector.send_fact_generator_in_batches(fact_gen=chain(*gen_list))
        except Exception as ex:
            log.warn("Exception sending datamaps to zing-connector. {}".format(ex))

    def fact_from_device(self, device):
        f = Fact()
        ctx = ObjectMapContext(device)
        f.metadata[FactKeys.CONTEXT_UUID_KEY] = ctx.uuid
        f.metadata[FactKeys.META_TYPE_KEY] = ctx.meta_type
        f.metadata[FactKeys.PLUGIN_KEY] = ctx.meta_type
        f.data[FactKeys.NAME_KEY] = ctx.name
        return f

    def fact_from_object_map(self, om, parent_device=None, relationship=None, context=None, dm_plugin=None):
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
        plugin_name = getattr(om, PLUGIN_NAME_ATTR, None) or dm_plugin
        if plugin_name:
            f.metadata[FactKeys.PLUGIN_KEY] = plugin_name

        # Hack in whatever extra stuff we need.
        om_context = (context or {}).get(om)
        if om_context is not None:
            self.apply_extra_fields(om_context, f)

        # FIXME temp solution until we are sure all zenpacks send the plugin
        if not f.metadata.get(FactKeys.PLUGIN_KEY):
            log.warn("Found fact without plugin information: {}".format(f.metadata))
            if f.metadata.get(FactKeys.META_TYPE_KEY):
                f.metadata[FactKeys.PLUGIN_KEY] = f.metadata[FactKeys.META_TYPE_KEY]
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
        fact.metadata[FactKeys.CONTEXT_UUID_KEY] = om_context.uuid
        fact.metadata[FactKeys.META_TYPE_KEY] = om_context.meta_type
        fact.data[FactKeys.NAME_KEY] = om_context.name

        if om_context.is_device:
            if om_context.mem_capacity is not None:
                fact.data[FactKeys.MEM_CAPACITY_KEY] = om_context.mem_capacity

DATAMAP_HANDLER_FACTORY = Factory(ZingDatamapHandler)
