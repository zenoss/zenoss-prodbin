##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from OFS.SimpleItem import SimpleItem

from Products.AdvancedQuery import And, Or, Not
from Products.Zuul.catalog.interfaces import IModelCatalogTool


default_value_converter = lambda value: value
last_part_of_path_value_converter = lambda value: value.split("/")[-1]


class LegacyFieldTranslation(object):
    def __init__(self, old, new, value_converter=None):
        self.old = old
        self.new = new
        self.value_converter = default_value_converter
        if value_converter is not None:
            self.value_converter = value_converter


class LegacyFieldsTranslator(object):
    def __init__(self):
        self.old_fields = {}
        self.new_fields = {}

    def add_translations(self, translations):
        """
        @param translations iterable of LegacyFieldTranslation
        """
        for translation in translations:
            self.add_field_translation(translation)

    def add_field_translation(self, field_translation):
        self.old_fields[field_translation.old] = field_translation
        self.new_fields[field_translation.new] = field_translation

    def translate(self, old=None, new=None):
        translation = None
        if old:
            translation = old # We dont have a translation
            if self.old_fields.get(old):
                translation = self.old_fields[old].new
        if new:
            translation = new # We dont have a translation
            if self.new_fields.get(new):
                translation = self.new_fields[new].old
        return translation

    def convert_value(self, old, value):
        if value and old in self.old_fields:
            converter = self.old_fields[old].value_converter
            value = converter(value)
        return value

    def get_old_field_names(self):
        return self.old_fields.keys()

    def get_new_field_names(self):
        return self.new_fields.keys()


DEVICE_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="getDeviceIp", new="text_ipAddress"),
    LegacyFieldTranslation(old="getPhysicalPath", new="uid"),
    LegacyFieldTranslation(old="titleOrId", new="name"),
    LegacyFieldTranslation(old="id", new="id"),
    LegacyFieldTranslation(old="getPrimaryId", new="uid"),
    LegacyFieldTranslation(old="path", new="path", value_converter=lambda x: [ tuple(p.split("/")) for p in x ]),
    # These fields need to be added
    # LegacyFieldTranslation(old="getDeviceClassPath", new="YYYYY"),
    # LegacyFieldTranslation(old="getAdminUserIds", new="YYYYYY"),
]


LAYER_2_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="macaddress", new="macaddress"),
    LegacyFieldTranslation(old="interfaceId", new="interfaceId"),
    LegacyFieldTranslation(old="deviceId", new="deviceId"),
    LegacyFieldTranslation(old="lanId", new="lanId"),
]


LAYER_3_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="networkId", new="networkId"),
    LegacyFieldTranslation(old="interfaceId", new="interfaceId", value_converter=last_part_of_path_value_converter),
    LegacyFieldTranslation(old="ipAddressId", new="ipAddressId"),
    LegacyFieldTranslation(old="deviceId", new="deviceId", value_converter=last_part_of_path_value_converter),
]


IP_SEARCH_CATALOG_TRANSLATIONS = [
    LegacyFieldTranslation(old="path", new="uid"),
    LegacyFieldTranslation(old="ipAddressAsInt", new="decimal_ipAddress", value_converter=str),
    LegacyFieldTranslation(old="id", new="id"),
]


TRANSLATIONS = {
    "deviceSearch"   : DEVICE_CATALOG_TRANSLATIONS,
    "layer2_catalog" : LAYER_2_CATALOG_TRANSLATIONS,
    "layer3_catalog" : LAYER_3_CATALOG_TRANSLATIONS,
    "ipSearch"       : IP_SEARCH_CATALOG_TRANSLATIONS,
}


class LegacyCatalogAdapter(SimpleItem):
    """
    Adapt the ZCatalog interface to use model catalog for searching.
    For every search it:
        - parses the query to replace the legacy catalog indexes (fields names)
          with model catalog field names
        - sends the request to model catalog
        - converts the brains received from model catalog adding legacy catalog
          field, updating the value if needed
    """
    def __init__(self, context, zcatalog_name=None):
        """
        @param context: context to instanciate IModelCatalogTool
        @param zcatalog_name: string representing the legacyCatalog we are adapting
        """
        self.context = context
        self.zcatalog_name = zcatalog_name
        self.translator = LegacyFieldsTranslator()
        if TRANSLATIONS.get(zcatalog_name):
            translations = TRANSLATIONS.get(zcatalog_name)
            self.translator.add_translations(translations)

    def _get_model_catalog(self):
        model_catalog = IModelCatalogTool(self.context)
        if self.zcatalog_name == "deviceSearch":
            model_catalog = model_catalog.devices
        elif self.zcatalog_name == "layer2_catalog":
            model_catalog = model_catalog.layer2
        elif self.zcatalog_name == "layer3_catalog":
            model_catalog = model_catalog.layer3
        elif self.zcatalog_name == "ipSearch":
            model_catalog = model_catalog.ips
        return model_catalog

    def __call__(self, query=None, **kw):
        return self.search(query, **kw)

    def searchResults(self, query=None, **kw):
        return self.search(query, **kw)

    def evalAdvancedQuery(self, query, **kw):
        # evalAdvancedQuery(query, sortSpecs=(), withSortValues=_notPassed)
        # @TODO try to do something with the sorting....
        return self.search(query)

    def _adapt_query(self, query):
        """
        modifies a query for a legacy catalog into a model catalog query
        @param query AdvancedQuery for the legacy catalog
        """
        # we need to translate the legacy catalog fields to model catalog fields
        if isinstance(query, And) or isinstance(query, Or):
            for q in query._subqueries:
                self._adapt_query(q)
        elif isinstance(query, Not):
            self._adapt_query(query._query)
        else:
            query._idx = self.translator.translate(old=query._idx)

    def _adapt_brains(self, search_results):
        """
        @param search_results model catalog search results
        @return 
        """
        converted_brains = []
        for brain in search_results:
            # add the legacy catalog fields to the brain
            for old_field_name in self.translator.get_old_field_names():
                new_field_name = self.translator.translate(old=old_field_name)
                value = getattr(brain, new_field_name)
                value = self.translator.convert_value(old_field_name, value)
                setattr(brain, old_field_name, value)
            converted_brains.append(brain)
        return converted_brains

    def search(self, query, sort_index=None, reverse=False, limit=None, **kw):
        model_catalog = self._get_model_catalog()
        search_kw = {}
        if query:
            self._adapt_query(query)
        if sort_index:
            search_kw["orderby"] = sort_index
        search_kw["reverse"] = reverse
        search_kw["limit"] = limit
        search_kw["fields"] = self.translator.get_new_field_names()
        search_results = model_catalog.search(query=query, **search_kw)
        legacy_brains = self._adapt_brains(search_results)
        return legacy_brains


"""
from Products.AdvancedQuery import Eq, And, Or, Not, MatchGlob, In
from Products.Zuul.catalog.legacy import LegacyCatalogAdapter

deviceSearch = LegacyCatalogAdapter(dmd, "deviceSearch")

def print_brains(brains):
    for b in brains:
           print b.getDeviceIp
           print b.getPhysicalPath
           print b.path
           print b.titleOrId
           print b.id
           print b.getPrimaryId
           print "---"


deviceSearch()
deviceSearch(Eq("titleOrId", "cisco2960G-50-5"))
deviceSearch(MatchGlob("titleOrId", "*cisco*"))
deviceSearch(In("titleOrId", ["cisco2960G-50-4", "cisco2960G-50-5"]))

searches = [ ]
searches.append(deviceSearch())
searches.append(deviceSearch(Eq("titleOrId", "cisco2960G-50-5")))
searches.append(deviceSearch(MatchGlob("titleOrId", "*cisco*")))

for s in searches:
    print_brains(s)
    print "\n\n"
"""


