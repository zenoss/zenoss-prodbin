##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp, MatchGlob

from Products.Zuul.catalog.model_catalog_tool_helper import ModelCatalogToolHelper

class ModelCatalogHelper(ModelCatalogToolHelper):
    """
    Helper class to get indexed information from model catalog
    """

    def __init__(self, model_catalog):
        super(ModelCatalogHelper, self).__init__(model_catalog)

    def _process_search_response(self, search_response, return_paths):
        results = search_response.results
        if return_paths:
            results = [ brain.getPath() for brain in results ]
        return results        

    def get_device_classes(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_device_classes()
        return self._process_search_response(search_response, return_paths)

    def get_event_classes(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_event_classes()
        return self._process_search_response(search_response, return_paths)

    def get_groups(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_groups()
        return self._process_search_response(search_response, return_paths)

    def get_locations(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_locations()
        return self._process_search_response(search_response, return_paths)

    def get_manufacturers(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_manufacturers()
        return self._process_search_response(search_response, return_paths)

    def get_systems(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_systems()
        return self._process_search_response(search_response, return_paths)

    def get_mib_organizers(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_mib_organizers()
        return self._process_search_response(search_response, return_paths)

    def get_mibs(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_mibs()
        return self._process_search_response(search_response, return_paths)

    def get_rrd_templates(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_rrd_templates()
        return self._process_search_response(search_response, return_paths)

    def get_process_organizers(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_process_organizers()
        return self._process_search_response(search_response, return_paths)

    def get_processes(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_processes()
        return self._process_search_response(search_response, return_paths)

    def get_report_organizers(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_report_organizers()
        return self._process_search_response(search_response, return_paths)

    def get_reports(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_reports()
        return self._process_search_response(search_response, return_paths)

    def get_services(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_services()
        return self._process_search_response(search_response, return_paths)

    def get_devices(self, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_devices()
        return self._process_search_response(search_response, return_paths)

    def get_device_components(self, device, return_paths=True):
        search_response = super(ModelCatalogHelper, self).get_device_components(device)
        return self._process_search_response(search_response, return_paths)

    def get_device_macs(self, device):
        fields = [ "macaddress" ]
        search_response = super(ModelCatalogHelper, self).get_device_interfaces(device, fields=fields)
        return [ brain.macaddress for brain in search_response.results if brain.macaddress ]

