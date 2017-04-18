
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob

class ModelCatalogHelper(object):
    """
    Helper class to get indexed information from model catalog
    """

    def __init__(self, model_catalog):
        self.model_catalog = model_catalog

    def _search(self, query, return_paths=True):
        search_response = self.model_catalog.search(query=query)
        results = search_response.results
        if return_paths:
            results = [ brain.getPath() for brain in results ]
        return results        

    def get_device_classes(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.DeviceClass.DeviceClass")
        return self._search(query, return_paths)

    def get_event_classes(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenEvents.EventClassInst.EventClassInst")
        return self._search(query, return_paths)

    def get_groups(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.DeviceGroup.DeviceGroup")
        return self._search(query, return_paths)

    def get_locations(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.Location.Location")
        return self._search(query, return_paths)

    def get_manufacturers(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self._search(query, return_paths)

    def get_systems(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.System.System")
        return self._search(query, return_paths)

    def get_manufacturers(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.Manufacturer.Manufacturer")
        return self._search(query, return_paths)

    def get_mib_organizers(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.MibOrganizer.MibOrganizer")
        return self._search(query, return_paths)

    def get_mibs(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.MibModule.MibModule")
        return self._search(query, return_paths)

    def get_rrd_templates(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.RRDTemplate.RRDTemplate")
        query = And(query, MatchGlob('uid', "/zport/dmd/Devices*"))
        return self._search(query, return_paths)

    def get_process_organizers(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.OSProcessOrganizer.OSProcessOrganizer")
        return self._search(query, return_paths)

    def get_processes(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.OSProcessClass.OSProcessClass")
        return self._search(query, return_paths)

    def get_report_organizers(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.ReportClass.ReportClass")
        return self._search(query, return_paths)

    def get_reports(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.Report.Report")
        return self._search(query, return_paths)

    def get_services(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.ServiceClass.ServiceClass")
        return self._search(query, return_paths)

    def get_devices(self, return_paths=True):
        query = Eq("objectImplements", "Products.ZenModel.Device.Device")
        return self._search(query, return_paths)




