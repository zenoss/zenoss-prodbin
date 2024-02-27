##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class DeviceConfigTable(object):
    """
    Manages device configuration data for a specific configuration service.
    """

    def __init__(self, app, scan_page_size=1000, mget_page_size=10):
        """Initialize a DeviceConfigTable instance."""
        self.__template = (
            "{app}:device:config:{{service}}:{{monitor}}:{{device}}".format(
                app=app
            )
        )
        self.__scan_count = scan_page_size
        self.__mget_count = mget_page_size

    def make_key(self, service, monitor, device):
        return self.__template.format(
            service=service, monitor=monitor, device=device
        )

    def exists(self, client, service, monitor, device):
        """Return True if configuration data exists for the given ID.

        :param service: Name of the configuration service.
        :type service: str
        :param monitor: Name of the monitor the device is a member of.
        :type monitor: str
        :param device: The ID of the device
        :type device: str
        :rtype: boolean
        """
        return client.exists(self.make_key(service, monitor, device))

    def scan(self, client, service="*", monitor="*", device="*"):
        """
        Return an iterable of tuples of (service, monitor, device).
        """
        pattern = self.make_key(service, monitor, device)
        result = client.scan_iter(match=pattern, count=self.__scan_count)
        return (tuple(key.rsplit(":", 3)[1:]) for key in result)

    def get(self, client, service, monitor, device):
        """Return the config data for the given config ID.

        If the config ID is not found, the default argument is returned.

        :type service: str
        :type monitor: str
        :type device: str
        :rtype: Union[IJellyable, None]
        """
        key = self.make_key(service, monitor, device)
        return client.get(key)

    def set(self, client, service, monitor, device, data):
        """Insert or replace the config data for the given config ID.

        If existing data for the device exists under a different monitor,
        it will be deleted.

        :param service: The name of the configuration service.
        :type service: str
        :param monitor: The ID of the performance monitor
        :type monitor: str
        :param device: The ID of the configuration
        :type device: str
        :param data: The serialized configuration data
        :type data: str
        :raises: ValueError
        """
        key = self.make_key(service, monitor, device)
        client.set(key, data)

    def delete(self, client, service, monitor, device):
        """Delete a key.

        This method does not fail if the key doesn't exist.

        :type service: str
        :type monitor: str
        :type device: str
        """
        key = self.make_key(service, monitor, device)
        client.delete(key)
