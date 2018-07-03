##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from transaction import commit

from Products.ZenModel.ZDeviceLoader import JobDeviceLoader
from Products.ZenHub.services.ModelerService import ModelerService
from Products.Zuul.utils import unbrain

from itertools import imap


class ZodbHelper(object):
    """
    Helper class to retrieve zodb objects/paths
    """

    def __init__(self, dmd):
        self.dmd = dmd

    def ppath(self, obj):
        return "/".join(obj.getPrimaryPath())

    def get_all_device_classes_path(self):
        prefix = '/'.join(self.dmd.Devices.getPrimaryPath())
        return [ "{0}{1}".format(prefix, dc).rstrip('/') for dc in self.dmd.Devices.getPeerDeviceClassNames() ]

    def get_event_classes(self, return_paths=True):
        ecs = self.dmd.Events.getInstances()
        if return_paths:
            ecs = [ self.ppath(ec) for ec in ecs ]
        return ecs

    def _get_organizer_names(self, root):
        """ helper method used to get groups, locations, systems """
        prefix = self.ppath(root)
        paths = []
        for name in root.getOrganizerNames():
            path = "{0}{1}".format(prefix, name).rstrip("/")
            paths.append(path)
        return paths

    def get_groups(self):
        return self._get_organizer_names(self.dmd.Groups)

    def get_locations(self):
        return self._get_organizer_names(self.dmd.Locations)

    def get_systems(self):
        return self._get_organizer_names(self.dmd.Systems)

    def get_manufacturers(self, return_paths=True):
        manufacturers = []
        for m in self.dmd.Manufacturers.getChildNodes():
            if hasattr(m, "meta_type") and m.meta_type == "Manufacturer":
                if return_paths:
                    manufacturers.append(self.ppath(m))
                else:
                    manufacturers.append(m)
        return manufacturers

    def get_rrd_templates(self, return_paths=True):
        templates = self.dmd.Devices.getAllRRDTemplatesPainfully()
        if return_paths:
            templates = [ self.ppath(t) for t in templates ]
        return templates

    def _get_organizers_of_type(self, root, meta_type, return_paths=True):
        oo = [ root ]
        oo.extend(root.getSubOrganizers())
        organizers = []
        for o in oo:
            if not meta_type or \
                hasattr(o, "meta_type") and o.meta_type == meta_type:
                organizers.append(o)
        return organizers

    def get_mib_organizers(self, return_paths=True):
        mib_organizers = self._get_organizers_of_type(self.dmd.Mibs, "MibOrganizer")
        if return_paths:
            mib_organizers = [self.ppath(o) for o in mib_organizers ] 
        return mib_organizers

    def get_mibs(self, return_paths=True):
        mibs = []
        mib_organizers = self.get_mib_organizers(return_paths=False)
        for mib_organizer in mib_organizers:
            mibs.extend(mib_organizer.mibs())
        if return_paths:
            mibs = [ self.ppath(mib) for mib in mibs ]
        return mibs

    def get_process_organizers(self, return_paths=True):
        process_organizers = self._get_organizers_of_type(self.dmd.Processes, "OSProcessOrganizer")
        if return_paths:
            process_organizers = [self.ppath(o) for o in process_organizers ]
        return process_organizers

    def get_processes(self, return_paths=True):
        processes = self.dmd.Processes.getSubOSProcessClassesGen()
        if return_paths:
            processes = [self.ppath(p) for p in processes ]
        return processes

    def get_report_organizers(self, return_paths=True):
        report_organizers = self._get_organizers_of_type(self.dmd.Reports, "")
        if return_paths:
            report_organizers = [self.ppath(o) for o in report_organizers ]
        return report_organizers

    def get_reports(self, return_paths=True):
        report_organizers = self.get_report_organizers(return_paths=False)
        reports = []
        for ro in report_organizers:
            reports.extend(ro.reports())
        if return_paths:
            reports = [self.ppath(r) for r in reports ]
        return reports

    def get_service_organizers(self, return_paths=True):
        organizers = self._get_organizers_of_type(self.dmd.Services, "ServiceOrganizer")
        if return_paths:
            organizers = [self.ppath(o) for o in organizers ]
        return organizers

    def get_services(self, return_paths=True):
        organizers = self.get_service_organizers(return_paths=False)
        services = []
        for o in organizers:
            services.extend(o.serviceclasses())
        if return_paths:
            services = [ self.ppath(s) for s in services ]
        return services

    def get_devices(self, return_paths=True):
        devices = self.dmd.Devices.getSubDevices_recursive()
        if return_paths:
            devices = [ self.ppath(d) for d in devices ]
        return devices

    def create_device_from_maps(self, ip, device_class, maps):
        device = JobDeviceLoader(self.dmd).load_device(ip, device_class, 'none', 'localhost', manageIp=ip)
        commit()
        ms = ModelerService(self.dmd, "localhost")
        for m in maps:
            ms.remote_applyDataMaps(ip, m, devclass=device_class)
        return device

    def get_device_components(self, device, return_paths=True):
        # use the component catalog since it wont be removed
        component_brains = device.componentSearch()
        return [ b.getPath() if return_paths else b.getObject() for b in component_brains  ]

    def get_device_macs(self, device):
        component_brains = device.componentSearch(meta_type="IpInterface")
        macs = [ obj.macaddress for obj in imap(unbrain, component_brains) if obj.macaddress ]
        return macs


