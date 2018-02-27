from json import JSONEncoder

from Products.DataCollector.plugins.DataMaps import RelationshipMap
from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.plugins.DataMaps import MultiArgs

from .shortid import shortid

import time


class FactKeys(object):
    CONTEXT_UUID_KEY = "contextUUID"
    META_TYPE_KEY = "meta_type"
    NAME_KEY = "name"
    MEM_CAPACITY_KEY = "mem_capacity"
    LOCATION_KEY = "location"


class Fact(object):

    @staticmethod
    def from_object_map(om, parent_device=None, relationship=None, context=None):
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
        f.update(d)
        if parent_device is not None:
            f.metadata["parent"] = parent_device.getUUID()
        if relationship is not None:
            f.metadata["relationship"] = relationship

        # Hack in whatever extra stuff we need.
        om_context = (context or {}).get(om)
        if om_context is not None:
            apply_extra_fields(om_context, f)

        return f

    @staticmethod
    def from_object(obj):
        f = Fact()
        fact_context = FactContext(obj)
        apply_extra_fields(fact_context, f)
        return f

    @staticmethod
    def from_device(device):
        f = Fact()
        ctx = FactContext(device)
        f.metadata[FactKeys.CONTEXT_UUID_KEY] = ctx.uuid
        f.metadata[FactKeys.META_TYPE_KEY] = ctx.meta_type
        f.data[FactKeys.NAME_KEY] = ctx.name
        return f

    def __init__(self):
        self.id = shortid()
        self.metadata = {}
        self.data = {}

    def update(self, other):
        self.data.update(other)

    def is_valid(self):
        return self.metadata.get(FactKeys.CONTEXT_UUID_KEY) is not None


class _FactEncoder(JSONEncoder):

    def _tweak_data(self, data_in):
        data_out = {}
        for k, v in data_in.iteritems():
            if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                # whatever comes in the list, tuple etc, needs to be scalar
                # if not, cast it to string
                values = []
                for x in v:
                    if not isinstance(x, (str, int, long, float, bool)):
                        x = str(x)
                    values.append(x)
                data_out[k] = sorted(values)
            elif isinstance(v, MultiArgs):
                data_out[k] = sorted(v.args)
            else:
                data_out[k] = [v]
        return data_out

    def default(self, o):
        if isinstance(o, Fact):
            return {
                "id": o.id,
                "data": self._tweak_data(o.data),
                "metadata": o.metadata,
                "timestamp": int(time.time())
            }
        if isinstance(o, MultiArgs):
            return o.args
        return JSONEncoder.default(self, o)


FactEncoder = _FactEncoder()


class FactContext(object):

    def __init__(self, obj):
        self.uuid = None
        self.meta_type = None
        self.name = None
        self.mem_capacity = None
        self.location = None
        self.is_device = False
        self._extract_relevant_fields_from_object(obj)

    def _extract_relevant_fields_from_object(self, obj):
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


def facts_from_datamap(device, dm, context):
    facts = []
    if isinstance(dm, RelationshipMap):
        for om in dm.maps:
            f = Fact.from_object_map(om, device, dm.relname, context=context)
            if f.is_valid():
                facts.append(f)
    elif isinstance(dm, ObjectMap):
        f = Fact.from_object_map(dm, context=context)
        if f.is_valid():
            facts.append(f)
    return facts


def serialize_facts(facts):
    if facts:
        encoded = FactEncoder.encode({"models": facts})
        return encoded


def apply_extra_fields(om_context, fact):
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


