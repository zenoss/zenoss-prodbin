from json import JSONEncoder

from Products.DataCollector.plugins.DataMaps import RelationshipMap
from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.plugins.DataMaps import MultiArgs

from .shortid import shortid

import time

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
            if not isinstance(v, (str, int, float, bool, list, tuple, MultiArgs, set)):
                del d[k]
        f.update(d)
        if parent_device is not None:
            f.metadata["parent"] = parent_device.getUUID()
        if relationship is not None:
            f.metadata["relationship"] = relationship

        # Hack in whatever extra stuff we need.
        obj = (context or {}).get(om)
        if obj is not None:
            apply_extra_fields(obj, f)

        return f

    def __init__(self):
        self.id = shortid()
        self.metadata = {}
        self.data = {}

    def update(self, other):
        self.data.update(other)


class _FactEncoder(JSONEncoder):

    def _tweak_data(self, data_in):
        data_out = {}
        for k, v in data_in.iteritems():
            if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                data_out[k] = sorted(v)
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


def serialize_datamap(device, dm, context):
    """
    Converts a datamap to a JSON-encoded list of facts.
    """
    facts = []
    if isinstance(dm, RelationshipMap):
        for om in dm.maps:
            facts.append(Fact.from_object_map(om, device, dm.relname, context=context))
    elif isinstance(dm, ObjectMap):
        facts.append(Fact.from_object_map(dm, context=context))
    if facts:
        encoded = FactEncoder.encode({"models": facts})
        return encoded

def apply_extra_fields(obj, fact):
    """
    A simple (temporary) hook to add extra information to a fact that isn't
    found in the datamap that triggered this serialization. This needs a proper
    event subscriber framework to be maintainable, so this will only work so
    long as the number of fields is pretty small.
    """
    from Products.ZenModel.Device import Device

    fact.metadata["contextUUID"] = obj.getUUID()
    fact.metadata["meta_type"] = obj.meta_type

    # titleOrId
    try:
        fact.data["name"] = obj.titleOrId()
    except Exception:
        pass

    if isinstance(obj, Device):
        # mem_capacity on devices
        try:
            fact.data["mem_capacity"] = obj.hw.totalMemory
        except Exception:
            pass

        # location on devices
        if "location" not in fact.data:
            try:
                loc = obj.location()
            except Exception:
                pass
            else:
                if loc is not None:
                    fact.data["location"] = loc.titleOrId()

