##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import re
import pkg_resources
from datetime import datetime, timedelta


from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.controlplane import configuration as cc_config

_default_interval = 86400.0  # seconds

def zenpack_names():
    for pkg in pkg_resources.iter_entry_points("zenoss.zenpacks"):
        yield pkg.module_name

def get_class_zenpack(cls):
    if hasattr(cls, "zenpack_name"):
        # ZPL class
        return cls.zenpack_name
    else:
        # Non-ZPL class

        # strip the class name hierarchy until we find one that is a zenpack
        classpath = cls.__module__.split(".")
        while classpath:
            classname = ".".join(classpath)
            if classname in zenpack_names():
                return classname
            del classpath[-1]

        return None


def get_zenpack_domain(zpname):
    has_it, override = entity_overrider.hasGetOverRideZenPackEntityDomains(zpname)
    if has_it:
        return override

    domain = re.sub(r"ZenPacks.zenoss\.PS\.", "", zpname)
    domain = re.sub(r"ZenPacks\.[^\.]+\.", "", domain)
    domain = re.sub(r"\.(base|core)$", "", domain, flags=re.IGNORECASE)
    domain = re.sub(r"(Base|Monitor)$", "", domain)
    domain = domain[0].upper() + domain[1:]

    return domain


_zpl_device_classes = None


def get_device_class_zenpack(dc):
    # Cache the device class -> zenpack data for ZPL-managed zenpacks.
    global _zpl_device_classes
    if _zpl_device_classes is None:
        _zpl_device_classes = {}

    for pack in dc.getDmd().ZenPackManager.packs():
        # although ZPL-managed device classes don't have a 'pack' relationship,
        # We can go the other direction.   The ZenPack object for this zenpack
        # has a copy of the device class definitions that were used to create
        # the DCs.
        if hasattr(pack, "device_classes"):
            for dcPath, dcSpec in pack.device_classes.iteritems():
                # We only consider a ZPL zenpack to own a device class if it is set
                # to create it on install *and* remove it on uninstall
                if dcSpec.create and dcSpec.remove:
                    _zpl_device_classes[dcPath] = pack.id

    # Device class owned by a zenpack?
    if dc.pack():
        return dc.pack().id

    # Device class owned by a ZPL zenpack?
    while dc:
        dcName = dc.getOrganizerName()
        if dcName == "/":
            break
        if dcName in _zpl_device_classes:
            zenpack_id = _zpl_device_classes[dcName]
            return zenpack_id
        dc = dc.getPrimaryParent()

    # Give up.   Though we may potentially want to consider other hard-coded
    # values for device classes that aren't owned by any zenpack.. Possibly
    # Base, at least for ones we know are part of the base system.
    return None


def get_class_entity_type(cls):
    has_it, entity_type = entity_overrider.hasGetOverRideEntityTypes(cls.meta_type)
    if has_it:
        return entity_type

    zenpack = get_class_zenpack(cls)
    domain = None
    if zenpack is not None:
        domain = get_zenpack_domain(zenpack)

        # Support specification of the entity type source attribute on a per-zenpack basis
        has_it, source = entity_overrider.hasGetOverRideZenPackEntityTypeSources(zenpack)
        if has_it:
            if source == "meta_type_direct":
                return cls.meta_type
            if source == "meta_type":
                return normalize_entity_type(domain, cls.meta_type)
            if source == "class_name":
                return normalize_entity_type(domain, cls.__name__)

    # default behavior:
    if hasattr(cls, "class_label"):
        return normalize_entity_type(domain, cls.class_label)
    return normalize_entity_type(domain, cls.__name__)


def normalize_entity_type(domain, name):
    namewords = re.split(r"[ \-\.]", name)
    name = "".join([x[0].upper() + x[1:] for x in namewords])

    if domain is not None and name.startswith(domain):
        # if the domain is also part of the entity type, strip the duplicate.
        name = name[len(domain) :]

    # remove non-alphanumeric characters
    name = re.sub(r"\W+", "", name)

    return name


def get_object_entity_domain(obj):
    zenpack = get_class_zenpack(obj.__class__)
    if zenpack is None:
        # Unable to figure out the zenpack based on the class of this object.
        # Usually this is because its device is using the generic Device class
        # (perhaps with monkeypatched relations)
        #        
        # We have nothing else to go off of other than the device class, so try
        # using that.  If it can't be found based upon that, this will return None.
        zenpack = get_device_class_zenpack(obj.deviceClass())

    if zenpack:
        return get_zenpack_domain(zenpack)

    # we haven't found it as part of any zenpack- if it's part of one of the system
    # default device classes that we've assigned domains to, use that.
    dc = obj.deviceClass()
    while dc:
        dcName = dc.getOrganizerName()
        if dcName == "/":
            break
        has_it, domain = entity_overrider.hasGetDefaultDeviceClassDomains(dcName)
        if has_it:
            return domain
        dc = dc.getPrimaryParent()

    # Otherwise, we have no identifiable domain.
    return None


def get_object_entity_type(obj):
    return get_class_entity_type(obj.__class__)


def get_object_entity_zenpack(obj):
    zenpack = get_class_zenpack(obj.__class__)
    if zenpack:
        return zenpack
    zenpack = get_device_class_zenpack(obj.deviceClass())

class EntityOverrider:
    def __init__(self, ttl=_default_interval):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl)
        self.key = cc_config.tenant_id + "_override_timestamp"
        self.entity_type_overrides = {
            "overRideEntityTypes": [],
            "overRideZenPackEntityDomains": [],
            "overRideZenPackEntityTypeSources": [],
            "defaultDeviceClassDomains": []
        }

    def get_cache(self):
        if self.key in self.cache:
            value = self.cache[self.key]
            diff = datetime.now() - value
            if diff.days * 86400 + diff.seconds < self.ttl.days * 86400 + self.ttl.seconds:
                return value
            else:
                del self.cache[self.key]
                return None
        else:
            return None

    def set_cache(self):
        self.cache[self.key] = datetime.now()

    def load_overrides(self):
        # TODO: determine actual location
        defaultOverridesPath = zenPath('Products/Zing/entity_overrides.json')
        with open(defaultOverridesPath, 'r') as f:
            self.entity_type_overrides = json.loads(f.read())

    def get_overrides(self):
        if self.get_cache() is None:
            self.load_overrides()
            self.set_cache()
        return self.entity_type_overrides

    def _hasGetOverRide(self, key, override):
        self.get_overrides()
        if key in self.entity_type_overrides[override]:
            return True, self.entity_type_overrides[override][key]
        return False, None

    def hasGetOverRideEntityTypes(self, entity_type):
        return self._hasGetOverRide(entity_type, 'overRideEntityTypes')

    def hasGetOverRideZenPackEntityDomains(self, zpname):
        return self._hasGetOverRide(zpname, 'overRideZenPackEntityDomains')

    def hasGetOverRideZenPackEntityTypeSources(self, zpname):
        return self._hasGetOverRide(zpname, 'overRideZenPackEntityTypeSources')

    def hasGetDefaultDeviceClassDomains(self, domain):
        return self._hasGetOverRide(domain, 'defaultDeviceClassDomains')


# singleton for keeping overrides in cache and convenience methods
entity_overrider = EntityOverrider()
