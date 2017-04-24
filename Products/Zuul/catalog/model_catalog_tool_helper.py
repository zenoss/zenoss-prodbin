##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob


class ModelCatalogToolHelper(object):
    """
    Helper class with methods that perform common searches in the model catalog
    """
    def __init__(self, model_catalog_tool):
        self.model_catalog = model_catalog_tool

    def get_device_classes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.DeviceClass.DeviceClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_event_classes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenEvents.EventClassInst.EventClassInst")
        return self.model_catalog.search(*args, **kwargs)

    def get_groups(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.DeviceGroup.DeviceGroup")
        return self.model_catalog.search(*args, **kwargs)

    def get_locations(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Location.Location")
        return self.model_catalog.search(*args, **kwargs)

    def get_manufacturers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self.model_catalog.search(*args, **kwargs)

    def get_systems(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.System.System")
        return self.model_catalog.search(*args, **kwargs)

    def get_manufacturers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self.model_catalog.search(*args, **kwargs)

    def get_mib_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.MibOrganizer.MibOrganizer")
        return self.model_catalog.search(*args, **kwargs)

    def get_mibs(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.MibModule.MibModule")
        return self.model_catalog.search(*args, **kwargs)

    def get_rrd_templates(self, *args, **kwargs):
        query = Eq("objectImplements", "Products.ZenModel.RRDTemplate.RRDTemplate")
        kwargs["query"] = And(query, MatchGlob('uid', "/zport/dmd/Devices*"))
        return self.model_catalog.search(*args, **kwargs)

    def get_process_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.OSProcessOrganizer.OSProcessOrganizer")
        return self.model_catalog.search(*args, **kwargs)

    def get_processes(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.OSProcessClass.OSProcessClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_report_organizers(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.ReportClass.ReportClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_reports(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Report.Report")
        return self.model_catalog.search(*args, **kwargs)

    def get_services(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.ServiceClass.ServiceClass")
        return self.model_catalog.search(*args, **kwargs)

    def get_devices(self, *args, **kwargs):
        kwargs["query"] = Eq("objectImplements", "Products.ZenModel.Device.Device")
        return self.model_catalog.search(*args, **kwargs)

    def _get_device_components(self, device, str_types, *args, **kwargs):
        types = set(["Products.ZenModel.DeviceComponent.DeviceComponent"])
        if str_types:
            types = types | set(str_types)
        query = [ Eq("objectImplements", str_type) for str_type in types ]
        query.append(Eq("deviceId", "/".join(device.getPrimaryPath())))
        kwargs["query"] = And(*query)
        return self.model_catalog.search(*args, **kwargs)

    def get_device_components(self, device, *args, **kwargs):
        return self._get_device_components(device, None, *args, **kwargs)

    def get_device_interfaces(self, device, *args, **kwargs):
        str_types = [ "Products.ZenModel.IpInterface.IpInterface" ]
        return self._get_device_components(device, str_types, *args, **kwargs)

    def search_mac(self, mac_address, fields=None):
        queries = []
        queries.append(Eq("objectImplements", "Products.ZenModel.IpInterface.IpInterface"))
        queries.append(Eq("macaddress", mac_address))
        return self.model_catalog.search(query=And(*queries), fields=fields)

