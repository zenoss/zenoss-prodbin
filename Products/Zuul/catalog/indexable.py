
from Acquisition import aq_base

from interfaces import IPathReporter

from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul.utils import getZProperties, allowedRolesAndUsers
from Products.ZenUtils.IpUtil import ipToDecimal

from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, ListOfStringsFieldType, IntFieldType
from zenoss.modelindex.field_types import DictAsStringsFieldType, LongFieldType, NotIndexedFieldType
from zenoss.modelindex.constants import NOINDEX_TYPE
from ZODB.POSException import ConflictError
from zope.interface import ro


"""
    @TODO:
        Review how and where we index IpAddresses and macs since currently we are indexing
        them in several places (Device, IpInterface, IpAddress)


    Set of abstract classes designed to add indexable attributes to zenoss objects. 
    Most methods start with idx_ to avoid conflicts with pre existing attributes/methods

        BaseIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |  idx_uid                   |  uid                    |       uid       |         |         |
            |  idx_id                    |  id                     |                 |         |         |
            |  idx_uuid                  |  uuid                   |                 |         |         |
            |  idx_name                  |  name                   |                 |         |         |
            |  idx_meta_type             |  meta_type              |                 |         |         |
            |  idx_path                  |  path                   |                 |         |         |
            |  idx_objectImplements      |  objectImplements       |                 |         |         |
            |  idx_allowedRolesAndUsers  |  allowedRolesAndUsers   |                 |         |         |
            ----------------------------------------------------------------------------------------------

        SearchIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |  idx_searchKeywords        |  searchKeywords         |                 |         |         |
            |  idx_searchExcerpt         |  searchExcerpt          |                 |         |         |
            |  idx_searchIcon            |  searchIcon             |                 |         |         |
            ----------------------------------------------------------------------------------------------


        DeviceIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |    ATTR_QUERY_NAME      |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |   idx_numeric_ipAddress    |   ipAddress             |                 |         |         |
            |   idx_text_ipAddress       |   text_ipAddress        |                 |         |         |
            |   idx_productionState      |   productionState       |                 |         |         |
            |   idx_macAddresses         |   macAddresses          |                 |         |         |
            |   idx_zProperties          |   zProperties           |                 |         |         |
            |   idx_device_searchExcerpt |   searchExcerpt         |                 |         |         |
            |   idx_device_searchKeywords|   searchKeywords        |                 |         |         |
            |   idx_device_searchIcon    |   searchIcon            |                 |         |         |
            ----------------------------------------------------------------------------------------------


        ComponentIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                   |  ATTR_QUERY_NAME      |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |  idx_monitored               |  monitored            |                 |         |         |
            |  idx_collectors              |  collectors           |                 |         |         |
            |  idx_deviceId                |  deviceId             |                 |         |         |
            |  idx_description             |  description          |                 |         |         |
            |  idx_component_searchKeywords|  searchKeywords       |                 |         |         |
            |  idx_component_searchExcerpt |  searchExcerpt        |                 |         |         |
            |  idx_compoment_searchIcon    |  searchIcon           |                 |         |         |
            ----------------------------------------------------------------------------------------------


        IpInterfaceIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                     |  ATTR_QUERY_NAME    |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |  idx_interfaceId               |   interfaceId       |                 |         |         |
            |  idx_numeric_ipAddress         |   ipAddress         |                 |         |         |
            |  idx_text_ipAddress            |   text_ipAddress    |                 |         |         |
            |  idx_macAddresses              |   macAddresses      |                 |         |         |
            |  idx_lanId                     |   lanId             |                 |         |         |
            |  idx_macaddress                |   macaddress        |                 |         |         |
            |  idx_component_searchKeywords  |   NOINDEX_TYPE      | DISABLE SUPERCLASS SPEC FIELD       |
            |  idx_ipInterface_searchKeywords|   searchKeywords    |                 |         |         |
            |  idx_compoment_searchExcerpt   |   NOINDEX_TYPE      | DISABLE SUPERCLASS SPEC FIELD       |
            |  idx_ipInterface_searchExcerpt |   searchExcerpt     |                 |         |         |
            
            ----------------------------------------------------------------------------------------------

        IpAddressIndexable:

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |   idx_interfaceId          |   interfaceId           |                 |         |         |
            |   idx_ipAddressId          |   ipAddressId           |                 |         |         |
            |   idx_networkId            |   networkId             |                 |         |         |
            |   idx_deviceId             |   deviceId              |                 |         |         |
            |   idx_ipAddressAsInt       |   ipAddressAsInt        |                 |         |         |
            |   idx_ipAddressAsText      |   ipAddressAsText       |                 |         |         |
            ----------------------------------------------------------------------------------------------


        ###########

            ----------------------------------------------------------------------------------------------
            |  ATTR_NAME                 |  ATTR_QUERY_NAME        |  FIELD NAME     | INDEXED |  STORED |
            ----------------------------------------------------------------------------------------------
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            |                            |                         |                 |         |         |
            ----------------------------------------------------------------------------------------------
"""

class BaseIndexable(object):    # ZenModelRM inherits from this class
    '''
    @indexed(StringFieldType(stored=True), attr_query_name="indexable"):
    def idx_base_indexable(self):
        return self.__class__.__name__
    '''

    @indexed(StringFieldType(stored=True), index_field_name="uid", attr_query_name="uid")
    def idx_uid(self):
        return aq_base(self).getPrimaryId()

    @indexed(StringFieldType(stored=True), attr_query_name="id")
    def idx_id(self):
        return self.id

    @indexed(StringFieldType(stored=True), attr_query_name="uuid")
    def idx_uuid(self):
        """
        Object's uuid.
        """
        try:
            # We don't need create() to update the global catalog, because by definition
            # this is only called when the object is going to be indexed.
            return IGlobalIdentifier(self).create(update_global_catalog=False)
        except ConflictError:
            raise
        except Exception:
            pass

    @indexed(StringFieldType(stored=True), attr_query_name="name")
    def idx_name(self):
        """
        The name of the object.
        """
        try:
            return self.titleOrId()
        except AttributeError:
            return self.id

    @indexed(str, attr_query_name="meta_type")
    def idx_meta_type(self):
        """
        Object's meta_type. Mostly used for backwards compatibility.
        """
        return aq_base(self).meta_type

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="path") # Device already has a method called path
    def idx_path(self):
        """
        Paths under which this object may be found. Subclasses should provide
        tuples indicating more paths (e.g. via a ToMany relationship).
        """
        return [ '/'.join(p) for p in IPathReporter(self).getPaths() ]

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="objectImplements")
    def idx_objectImplements(self):
        """
        All interfaces and classes implemented by an object.
        """
        dottednames = set()
        # Add the highest five classes in resolution order. 5 is
        # an arbitrary number; essentially, we only care about indexing
        # Zenoss classes, and our inheritance tree isn't that deep. Past
        # 5 we index a bunch of ObjectManager, Persistent, etc., which
        # we'll never use, and enact a significant performance penalty
        # when inserting keywords into the index.

        for kls in ro.ro(self.__class__):  
            # @TODO review. had some issues with picking only the top 5
            # instead we get anything from Products or Zenpacks
            if kls.__module__.startswith("Products") or kls.__module__.startswith("ZenPacks"):
                dottednames.add('%s.%s' % (kls.__module__, kls.__name__))
        return list(dottednames)

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="allowedRolesAndUsers")
    def idx_allowedRolesAndUsers(self):
        """
        Roles and users with View permission.
        """
        return allowedRolesAndUsers(self)


class DeviceIndexable(object):   # Device inherits from this class
    
    def _idx_get_ip(self):
        if hasattr(self, 'getManageIp') and self.getManageIp():
            return self.getManageIp().partition('/')[0]
        else:
            return None

    @indexed(LongFieldType(stored=True), attr_query_name="ipAddress") # Ip address as number
    def idx_numeric_ipAddress(self):
        ip = self._idx_get_ip()
        if ip:
            return ipToDecimal(ip)
        else:
            return None

    @indexed(StringFieldType(stored=True), attr_query_name="text_ipAddress")
    def idx_text_ipAddress(self):
        return self._idx_get_ip()

    @indexed(str, attr_query_name="productionState")
    def idx_productionState(self):
        return str(self.productionState)

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="macAddresses")
    def idx_macAddresses(self):
        return self.getMacAddresses()

    @indexed(DictAsStringsFieldType(indexed=False), attr_query_name="zProperties")
    def idx_zProperties(self):
        return getZProperties(self)

    """    IModelSearchable indexes  """

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="searchKeywords")
    def idx_device_searchKeywords(self):
        keywords = []
        keywords.append(self.titleOrId())
        keywords.append("monitored" if self.monitorDevice() else "unmonitored")
        keywords.extend( [ self.manageIp, self.hw.serialNumber, self.hw.tag,
            self.getHWManufacturerName(), self.getHWProductName(),
            self.getOSProductName(), self.getOSManufacturerName(),
            self.getHWSerialNumber(), self.getPerformanceServerName(),
            self.getProductionStateString(), self.getPriorityString(),
            self.getLocationName(), self.snmpSysName, self.snmpLocation ] )
        keywords.extend(self.getSystemNames())
        keywords.extend(self.getDeviceGroupNames())
        keywords.append(self.meta_type)

        """
        @TODO What can we do with IpAdresses??
        o = self._context
        ipAddresses = []
        try:
            # If we find an interface IP address, link it to a device
            if hasattr(o, 'os') and hasattr(o.os, 'interfaces'):
                ipAddresses = chain(*(iface.getIpAddresses()
                                       for iface in o.os.interfaces()))
                # fliter out localhost-ish addresses
                ipAddresses = ifilterfalse(lambda x: x.startswith('127.0.0.1/') or
                                                     x.startswith('::1/'),
                                           ipAddresses)
        except Exception:
            ipAddresses = []
        """
        unique_keywords = { keyword for keyword in keywords if keyword }
        return list(unique_keywords)

    @indexed(StringFieldType(stored=True), attr_query_name="searchExcerpt")
    def idx_device_searchExcerpt(self):
        if self.manageIp:
            return '{0} <span style="font-size:smaller">({1})</span>'.format(self.titleOrId(), self.manageIp)
        else:
            return self.titleOrId()

    @indexed(StringFieldType(stored=True), attr_query_name="searchIcon")
    def idx_device_searchIcon(self):
        return self.getIconPath()


class ComponentIndexable(object):     # DeviceComponent inherits from this class

    @indexed(bool, attr_query_name="monitored")
    def idx_monitored(self):
        return True if self.monitored() else False

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="collectors")
    def idx_collectors(self):
        cols = self.getCollectors()
        if cols:
            return [ col for col in cols if col ]
        else:
            return []

    @indexed(StringFieldType(stored=True), attr_query_name="deviceId")
    def idx_deviceId(self):
        """ device the component belongs to """
        device_id = None
        if self.device():
            device_id = self.device().idx_uid()
        return device_id

    @indexed(StringFieldType(stored=True), attr_query_name="description")
    def idx_description(self):
        """ device the component belongs to """
        description = None
        if self.description:
            description = self.description
        return description

    """    IModelSearchable indexes  """

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="searchKeywords")
    def idx_component_searchKeywords(self):
        keywords = set()
        keywords.add(self.name())
        keywords.add(self.meta_type)
        keywords.add(self.titleOrId())
        keywords.add("monitored" if self.idx_monitored() else "unmonitored")
        return [ k for k in keywords if k ]

    @indexed(StringFieldType(stored=True), attr_query_name="searchExcerpt")
    def idx_component_searchExcerpt(self):
        text = '{0} <span style="font-size:smaller">({1})</span>'
        return text.format(self.name(), self.device().titleOrId())

    @indexed(StringFieldType(stored=True), attr_query_name="searchIcon")
    def idx_compoment_searchIcon(self):
        return self.getIconPath()


class IpInterfaceIndexable(ComponentIndexable): # IpInterface inherits from this class
    
    @indexed(StringFieldType(stored=True), attr_query_name="interfaceId")
    def idx_interfaceId(self):
        interface_id = None
        if self.interfaceId():
            interface_id = self.interfaceId()
        return interface_id

    def _idx_get_ip(self):
        if hasattr(self, 'getIpAddress') and self.getIpAddress():
            return self.getIpAddress().partition('/')[0]
        else:
            return None

    @indexed(LongFieldType(stored=True), attr_query_name="ipAddress") # Ip address as number
    def idx_numeric_ipAddress(self):
        ip = self._idx_get_ip()
        if ip:
            return ipToDecimal(ip)
        else:
            return None

    @indexed(StringFieldType(stored=True), attr_query_name="text_ipAddress")
    def idx_text_ipAddress(self):
        return self._idx_get_ip()

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="macAddresses")
    def idx_macAddresses(self):
        return [self.macaddress]

    """    IModelSearchable indexes  """

    index("idx_component_searchKeywords", NOINDEX_TYPE) # disable ComponentIndexable implementation

    @indexed(ListOfStringsFieldType(stored=True), attr_query_name="searchKeywords")
    def idx_ipInterface_searchKeywords(self):
        if self.titleOrId() in ('lo', 'sit0'):
            # Ignore noisy interfaces
            return []
        # We don't need to include the ip addresses for this interface, because
        # all ips on a device are included in the keywords of every one of its
        # components.
        keywords = ComponentIndexable.idx_component_searchKeywords(self)
        keywords.append(self.description)
        return keywords

    index("idx_component_searchExcerpt", NOINDEX_TYPE) # disable ComponentIndexable implementation

    @indexed(StringFieldType(stored=True), attr_query_name="searchExcerpt")
    def idx_ipInterface_searchExcerpt(self):
        parent_excerpt = ComponentIndexable.idx_component_searchExcerpt(self)
        return "{0} {1}".format(parent_excerpt, ' '.join([ self.description ]))

    # We dont need searchIcon bc the superclass ComponentIndexable already has it

    """ Layer 2 catalog indexes """

    @indexed(StringFieldType(stored=True), attr_query_name="lanId")
    def idx_lanId(self):
        lan_id = None
        if self.lanId() and self.lanId()!="None":
            lan_id = self.lanId()
        return lan_id

    @indexed(StringFieldType(stored=True), attr_query_name="macaddress")
    def idx_macaddress(self):
        return self.macaddress


class IpAddressIndexable():  # IpAddress inherits from this class

    """ Layer 3 catalog indexes """

    @indexed(StringFieldType(stored=True), attr_query_name="interfaceId")
    def idx_interfaceId(self):
        interface_id = None
        if self.interfaceId():
            interface_id = self.interfaceId()
        return interface_id

    @indexed(StringFieldType(stored=True), attr_query_name="ipAddressId")
    def idx_ipAddressId(self):
        return self.ipAddressId()

    @indexed(StringFieldType(stored=True), attr_query_name="networkId")
    def idx_networkId(self):
        return self.networkId()

    @indexed(StringFieldType(stored=True), attr_query_name="deviceId")
    def idx_deviceId(self):
        """ device the ipaddress belongs to. Since IpAddress does not inherit from DeviceComponent """
        device_id = None
        if self.device():
            device_id = self.device().idx_uid()
        return device_id

    @indexed(LongFieldType(stored=True), attr_query_name="ipAddressAsInt")
    def idx_ipAddressAsInt(self):
        return int(self.ipAddressAsInt())

    @indexed(StringFieldType(stored=True), attr_query_name="ipAddressAsText")
    def idx_ipAddressAsText(self):
        return self.getIpAddress()


""" @TODO : Do we need to define this
class FileSystemIndexable(ComponentIndexable):

    def name(self):
        return self.name()
"""

