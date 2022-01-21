##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020-2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import httplib
import json
import logging
import os
import urlparse

from twisted.internet import defer, reactor, ssl
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath
from twisted.web import client
from zope.component import queryUtility

from Products.ZenEvents import Event
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from .interfaces import IEventService
from .ExpiringCache import ExpiringCache

_CFG_URL = "cyberark-url"
_CFG_PORT = "cyberark-port"
_CFG_QUERY = "cyberark-query"
_CFG_CACHE_TTL = "cyberark-cache-ttl"
_CFG_CERT_PATH = "cyberark-cert-path"

_default_config = {
    _CFG_PORT: 443,
    _CFG_QUERY: "/AIMWebService/api/Accounts?appid=",
    _CFG_CACHE_TTL: 300,
    _CFG_CERT_PATH: "/var/zenoss/cyberark",
}

_required_configs = (_CFG_URL,)
_cyberark_flag = "_has_cyberark_queries"

log = logging.getLogger("zen.cyberark")


def get_cyberark():
    global_config = getGlobalConfiguration()

    if not _check_config(global_config):
        log.info("CyberArk unavailable. No configuration found.")
        return

    try:
        cyberark = CyberArk.from_dict(
            _Config(global_config, _default_config),
        )
    except Exception:
        log.exception("CyberArk failed to initialize.")
    else:
        log.info("CyberArk ready.")
        return cyberark


def _check_config(config):
    valid = True
    for prop in _required_configs:
        if prop not in config:
            if log.getEffectiveLevel() <= logging.DEBUG:
                log.warn(
                    "Required CyberArk config property not found: %s",
                    prop,
                )
            valid = False
    return valid


class _Config(object):
    """Wraps a dict to provide default values from a provided dict.
    """

    def __init__(self, cfg, defaults):
        self._config = cfg
        self._default = defaults

    def get(self, key):
        return self._config.get(key, self._default.get(key))


class CyberArk(object):
    """Top level API for updating device configs from CyberArk.
    """

    @staticmethod
    def from_dict(conf):
        """Returns a new CyberArk object.

        :param conf: Contains the CyberArk configuration data
        :type conf: A dict-like object providing the 'get' method.
        """
        manager = CyberArkManager.from_dict(conf)
        query = conf.get(_CFG_QUERY)
        log.debug("Using config '%s' = '%s'", _CFG_QUERY, query)
        return CyberArk(query, manager)

    def __init__(self, query, manager):
        """Initializes a CyberArk instance.

        :param str query: The base CyberArk URL query.
        :param CyberArkManager manager:
        """
        self._manager = manager
        self._base_query = query

    @defer.inlineCallbacks
    def update_datasource(self, task):
        if hasattr(task, 'config'):
            if hasattr(task.config, 'datasources') and task.config.datasources:
                ds0 = task.config.datasources[0]
                # we update single config first, to get values for other
                # configs from cache
                yield self.update_config(ds0)
                for ds in task.config.datasources[1:]:
                    yield self.update_config(ds)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def update_config(self, config, device_info_object=None):
        """Updates particular zproperties of the given device config.

        The particular zproperties are identifiable by their value.  If a
        zproperty's value starts with the base CyberArk URL query, then
        that value is replaced with the value found in CyberArk.

        If the value is not found in CyberArk, an empty string is used as
        the value of the zproperty.

        :param config: The device config object.
        :param device_info_object: Optional object to pass in if config's
            device ID can't be guessed from the config.
        """
        if not device_info_object:
            device_info_object = config
        deviceId = _get_device_id(device_info_object)

        has_queries = getattr(config, _cyberark_flag, None)

        # A value of None for the cyberark flag indicates we need to
        # identify all the zproperties that are CyberArk queries.
        if has_queries is None:
            has_queries = self._add_queries(deviceId, config)
            setattr(config, _cyberark_flag, has_queries)

        # A value of False for the cyberark flag indicates there are no
        # zproperties that are CyberArk queries, so return.
        if has_queries is False:
            defer.returnValue(None)

        # There are zproperties having a CyberArk query, so update the
        # zproperty value from CyberArk.
        yield self._manager.update(deviceId)
        for prop in self._manager.getPropertiesFor(deviceId):
            value = prop.value if prop.value is not None else ""
            setattr(config, prop.name, value)

    def _add_queries(self, deviceId, config):
        has_queries = False
        for name, value in vars(config).items():
            if (
                isinstance(value, basestring)
                and value.startswith(self._base_query)
            ):
                self._manager.add(deviceId, name, value.strip())
                has_queries = True
        return has_queries


def _get_device_id(info):
    # This is a hack to determine the device ID.
    # It would be better if the caller passed in the device ID since it
    # already knows that value.

    # zencommand and zenperfsnmp
    if hasattr(info, '_devId'):
        return info._devId
    # zenpython
    if hasattr(info, 'device'):
        return info.device
    # zenmodeler
    if hasattr(info, 'id'):
        return info.id
    # zenvsphere
    if hasattr(info, 'configId'):
        return info.configId
    return 'default'


class CyberArkManager(object):
    """Manages the integration with CyberArk.
    """

    @staticmethod
    def from_dict(conf):
        """Returns a new CyberArkManager object.

        :param conf: Contains the CyberArk configuration data
        :type conf: A dict-like object providing the 'get' method.
        """
        client = CyberArkClient.from_dict(conf)
        cache_ttl = conf.get(_CFG_CACHE_TTL)
        log.debug("Using config '%s' = '%s'", _CFG_CACHE_TTL, cache_ttl)
        return CyberArkManager(cache_ttl, client)

    def __init__(self, cache_ttl, client):
        """Initializes a CyberArkManager instance.

        :param int cache_ttl: The time-to-live config for the cache
        :param CyberArkClient client: Handles communication with CyberArk
        """
        ttl = int(cache_ttl)
        self._client = client
        self._cache = ExpiringCache(ttl)
        self._properties = {}
        self._eventService = queryUtility(IEventService)
        self._handlers = {
            httplib.OK: self._handle_ok,
            httplib.NOT_FOUND: self._handle_not_found,
            httplib.FORBIDDEN: self._handle_forbidden,
        }

    def add(self, deviceId, zprop, query):
        """Registers a zproperty configured with a CyberArk query.

        :param str deviceId: Identifies the device
        :param str zprop: Identifies the zproperty
        :param str query: The CyberArk query string
        """
        key = (deviceId, zprop)
        prop = self._properties.get(key)
        if prop is None:
            self._properties[key] = CyberArkProperty(deviceId, zprop, query)
        else:
            # Only update the query if the property already exists.
            prop.query = query

    def getPropertiesFor(self, deviceId):
        """Returns a list of CyberArkProperty objects for the given device.

        :param str deviceId: Identifies the device
        """
        return [
            prop
            for prop in self._properties.itervalues()
            if prop.deviceId == deviceId
        ]

    @defer.inlineCallbacks
    def update(self, deviceId):
        """Updates the cache for device's registered zproperties.

        :param str deviceId: Identifies the device.
        """
        properties = self.getPropertiesFor(deviceId)
        for prop in properties:
            # No need to query CyberArk if the cached value is good.
            if prop.query in self._cache:
                log.debug(
                    "Using cached value  device=%s zproperty=%s query=%s",
                    prop.deviceId, prop.name, prop.query,
                )
                if prop.value is None:
                    prop.value = self._cache.get(prop.query)
                continue
            try:
                status, result = yield self._client.request(prop.query)
            except Exception as ex:
                log.error(
                    "Failed to execute CyberArk query - %s  "
                    "device=%s zproperty=%s query=%s",
                    ex, prop.deviceId, prop.name, prop.query,
                )
                _log_previously_used_value(prop)
                event = _makeErrorEvent(
                    prop.deviceId,
                    "CyberArk request for zproperty %s failed: %s" % (
                        prop.name, ex,
                    ),
                )
            else:
                handler = self._handlers.get(status, self._handle_error)
                event = handler(status, prop, result)
            self._eventService.sendEvent(event)

    def _handle_ok(self, status, prop, result):
        result = result.strip()
        if not result:
            log.error(
                "Empty response  "
                "device=%s zproperty=%s query=%s",
                prop.deviceId,
                prop.name,
                prop.query,
            )
            _log_previously_used_value(prop)
            return _makeErrorEvent(
                prop.deviceId,
                "Empty response from CyberArk for zproperty %s" % prop.name,
            )
        try:
            decoded = json.loads(result)
        except Exception as ex:
            log.error(
                "Failed to decode message body: %s  "
                "device=%s zproperty=%s query=%s body=%s",
                ex,
                prop.deviceId,
                prop.name,
                prop.query,
                result,
            )
            _log_previously_used_value(prop)
            return _makeErrorEvent(
                prop.deviceId,
                "Invalid message from CyberArk for zproperty %s" % prop.name,
            )
        else:
            prop.value = decoded.get("Content")
            self._cache.set(prop.query, prop.value)
            return _makeClearEvent(prop.deviceId)

    def _handle_not_found(self, status, prop, value):
        log.error(
            "Invalid value for 'object' or 'safe' parameters in query  "
            "device=%s zproperty=%s query=%s",
            prop.deviceId,
            prop.name,
            prop.query,
        )
        _log_previously_used_value(prop)
        return _makeErrorEvent(
            prop.deviceId,
            "No object found for zproperty %s in CyberArk" % prop.name,
        )

    def _handle_forbidden(self, status, prop, value):
        log.error(
            "Access not allowed (invalid value appid parameter?)  "
            "device=%s zproperty=%s query=%s",
            prop.deviceId,
            prop.name,
            prop.query,
        )
        _log_previously_used_value(prop)
        return _makeErrorEvent(prop.deviceId, "Access not allowed")

    def _handle_error(self, status, prop, value):
        log.error(
            "CyberArk request failed  "
            "status=%s %s device=%s zproperty=%s query=%s ",
            status,
            httplib.responses.get(status),
            prop.deviceId,
            prop.name,
            prop.query,
        )
        _log_previously_used_value(prop)
        return _makeErrorEvent(
            prop.deviceId,
            "CyberArk query for %s failed with HTTP error %s %s" % (
                prop.name,
                status,
                httplib.responses.get(status),
            ),
        )


def _log_previously_used_value(prop):
    if prop.value is not None:
        log.debug(
            "Using previously retrieved value  "
            "device=%s zproperty=%s query=%s",
            prop.deviceId,
            prop.name,
            prop.query,
        )


_base_event_data = {
    "eventClass": "/Status",
    "eventKey": "cyberark",
}


def _makeClearEvent(deviceId):
    return dict(_base_event_data, **{
        "device": deviceId,
        "summary": "Successful CyberArk collection.",
        "severity": Event.Clear,
    })


def _makeErrorEvent(deviceId, summary):
    return dict(_base_event_data, **{
        "device": deviceId,
        "summary": summary,
        "severity": Event.Error,
    })


class CyberArkClient(object):
    """Provides an API to communicate with CyberArk.
    """

    @staticmethod
    def from_dict(conf):
        """Returns a new CyberArkClient object.

        :param conf: Contains the CyberArk configuration data
        :type conf: A dict-like object providing the 'get' method.
        """
        url = unicode(conf.get(_CFG_URL))
        port = conf.get(_CFG_PORT)
        cert_path = conf.get(_CFG_CERT_PATH)
        log.debug("Using config '%s' = '%s'", _CFG_URL, url)
        log.debug("Using config '%s' = '%s'", _CFG_PORT, port)
        log.debug("Using config '%s' = '%s'", _CFG_CERT_PATH, cert_path)
        options = load_certificates(url, cert_path)
        return CyberArkClient(url=url, port=port, options=options)

    def __init__(self, url, port, options):
        """Initializes a CyberArkClient instance.

        :param str url: https://hostname
        :param int port: The port number to use
        :param options: Used for creating the connection to CyberArk
        :type options: twisted.internet.interfaces.IOpenSSLClientConnectionCreator  # noqa E501
        """
        port = int(port)
        parts = urlparse.urlsplit(url)
        if (
            (parts.scheme == "https" and port == 443)
            or (parts.scheme == "http" and port == 80)
        ):
            self.base_url = "%s://%s" % (parts.scheme, parts.hostname)
        else:
            self.base_url = "%s://%s:%s" % (parts.scheme, parts.hostname, port)
        self.base_path = parts.path
        self.agent = client.Agent(reactor, contextFactory=MyPolicy(options))

    @defer.inlineCallbacks
    def request(self, query):
        """Executes a query against CyberArk.

        A successful query returns a tuple containing the HTTP result code
        and the body of the response.  Not finding a value counts as a
        successful query with the HTTP result code equaling 404.

        An exception is raised if the request could not be communicated to
        CyberArk.

        :param str query: The URL query
        :returns: (int, str)
        """
        if query.startswith("/"):
            query = query[1:]
        path = "/".join((self.base_path, query))
        url = urlparse.urljoin(self.base_url, path)
        log.debug("Request url: %s", url)

        try:
            response = yield self.agent.request("GET", url, None, None)
        except Exception as ex:
            log.exception("Request failed url=%s", url)
            raise Failure(ex)

        try:
            result = yield client.readBody(response)
        except Exception as ex:
            log.exception("Failed to read message body  url=%s", url)
            raise Failure(ex)

        defer.returnValue((response.code, result))


def load_certificates(url, cert_path):
    hostname = unicode(urlparse.urlsplit(url).hostname)
    authority = ssl.Certificate.loadPEM(
        FilePath(os.path.join(cert_path, "RootCA.crt")).getContent()
    )
    client_cert = FilePath(os.path.join(cert_path, "client.crt")).getContent()
    client_key = FilePath(os.path.join(cert_path, "client.pem")).getContent()
    client_certificate = ssl.PrivateCertificate.loadPEM(
        client_cert + client_key
    )
    return ssl.optionsForClientTLS(
        hostname,
        trustRoot=authority,
        clientCertificate=client_certificate,
    )


class CyberArkProperty(object):
    """A zproperty that has its value stored in CyberArk.

    The 'value' attribute will contain the last value read from CyberArk.
    The 'value' attribute will be None if a value has not been read.
    """

    __slots__ = ("deviceId", "name", "value", "query")

    def __init__(self, deviceId, zprop, query):
        self.deviceId = deviceId
        self.name = zprop
        self.value = None
        self.query = query


class MyPolicy(client.BrowserLikePolicyForHTTPS):
    def __init__(self, options, *args, **kwargs):
        super(MyPolicy, self).__init__(*args, **kwargs)
        self.options = options

    def creatorForNetloc(self, hostname, port):
        return self.options
