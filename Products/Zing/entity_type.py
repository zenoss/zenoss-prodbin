##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re
import pkg_resources
from pkg_resources import Requirement

OVERRIDE_ENTITY_TYPE = {
    # meta_type -> entity type
    # VSphere
    "vSphereDistributedVirtualPortgroup": "DistributedVirtualPortgroup",
    "vSphereDistributedVirtualSwitch": "DistributedVirtualSwitch",
    "vSphereEndpoint": "Endpoint",
    "vSphereHostSystem": "HostSystem",
    "vSphereStandalone": "Standalone",
    "vSphereVnic": "Vnic",
    # CiscoUCS
    "UCSStorageLocalDisk": "LocalDisk",
    "UCSStorageVirtualDrive": "VirtualDrive",
    "UCSVnicEther": "VirtualNic",
    "UCSAdaptorUnit": "NetworkAdaptor",
    "UCSCommonPort": "CommonPort",
}

OVERRIDE_ZENPACK_ENTITY_DOMAIN = {
    # zenpack id -> entity domain
    "ZenPacks.zenoss.AixMonitor": "AIX"
}

OVERRIDE_ZENPACK_ENTITY_TYPE_SOURCE = {
    # by default, entity type names are derived from the class label, or its
    # name if that is not available.
    #
    # In some cases, we may wish to have it use the meta type or class name
    # preferentially.
    # entity domain -> "meta_type_direct", "meta_type" | "class_name" | "default"
    # - meta_type_direct means to use the meta_type as the entity type, as is.
    # - meta_type means to use the meta_type, but normalize its capitalization.
    "ZenPacks.zenoss.Kubernetes": "meta_type_direct"
}

DEFAULT_DEVICE_CLASS_DOMAIN = {
    '/Network': "Network",
    '/Ping': "Ping",
    '/Power/UPS': "UPS",
    '/Printer': "Printer",
    '/Server/IBM': "AIX",
    '/Server/Linux': "Linux",
    '/Server/SSH/AIX': "AIX",
    '/Server/Scan': "Scanner",
    '/Server/VMware': "VSphere",
    '/Server/Windows': "Microsoft.Windows",
    '/Storage/EMC': "EMC"
}

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
    if zpname in OVERRIDE_ZENPACK_ENTITY_DOMAIN:
        return OVERRIDE_ZENPACK_ENTITY_DOMAIN[zpname]

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
    if cls.meta_type in OVERRIDE_ENTITY_TYPE:
        return OVERRIDE_ENTITY_TYPE[cls.meta_type]

    zenpack = get_class_zenpack(cls)
    domain = None
    if zenpack is not None:
        domain = get_zenpack_domain(zenpack)

        # Support specification of the entity type source attribute on a per-zenpack basis
        if zenpack in OVERRIDE_ZENPACK_ENTITY_TYPE_SOURCE:
            source = OVERRIDE_ZENPACK_ENTITY_TYPE_SOURCE[zenpack]
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
        if dcName in DEFAULT_DEVICE_CLASS_DOMAIN:
            return DEFAULT_DEVICE_CLASS_DOMAIN[dcName]
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
