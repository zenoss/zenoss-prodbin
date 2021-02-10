##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020-2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import distutils
import json
import logging
import os
import urlparse

from twisted.internet import defer, reactor, ssl
from twisted.internet.protocol import Protocol
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath
from twisted.web import client

import zope.component

from Products.ZenEvents import Event
from Products.ZenCollector.interfaces import IEventService
from Products.ZenCollector.ExpiringCache import ExpiringCache
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

CERTIFICATES_PATH = '/opt/zenoss/cyberark'
CYBER_ARK_PORT = 443
CYBER_ARK_QUERY = '/AIMWebService/api/Accounts?appid='
CYBERARK_CACHE_TTL = 300
LONG_LIVE_CACHE_MULTIPLIER = 72

log = logging.getLogger('zen.CyberArk')


def check_config(config):
    valid = True
    required = ('cyberark-url',)
    for prop in required:
        if prop not in config:
            log.warning('Required property: %s for CyberArk'
                        'in config is not set', prop)
            valid = False
    return valid


def get_cyberark():
    cyberark = None
    global_config = getGlobalConfiguration()
    if global_config.get('cyberark-url') and check_config(global_config):
        try:
            cyberark = CyberArk(global_config)
            log.info('Initialization of CyberArk was sucessful')
        except Exception as e:
            log.error('Error while CyberArk initialization: %s', e)
    else:
        log.debug('Initialization of CyberArk was omitted')
    return cyberark


def sleep(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d


class CyberArk(object):
    """Provides an access to CyberArk"""

    def __init__(self, config):
        self.manager = CyberArkManager(
            url=unicode(config.get('cyberark-url')),
            port=config.get('cyberark-port', CYBER_ARK_PORT),
            cert_path=config.get('cyberark-cert-path', CERTIFICATES_PATH),
            cache_ttl=config.get('cyberark-cache-ttl', CYBERARK_CACHE_TTL),
            test_mode=config.get('cyberark-test-mode', 'off'),
        )
        self.cyberark_query = config.get('cyberark-query', CYBER_ARK_QUERY)

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
        device = None
        if not device_info_object:
            device_info_object = config

        # zencommand and zenperfsnmp
        if hasattr(device_info_object, '_devId') and not device:
            device = device_info_object._devId
        # zenpython
        if hasattr(device_info_object, 'device') and not device:
            device = device_info_object.device
        # zenmodeler
        if hasattr(device_info_object, 'id') and not device:
            device = device_info_object.id
        # zenvsphere
        if hasattr(device_info_object, 'configId') and not device:
            device = device_info_object.configId

        if not device:
            device = 'default'
        yield self._update_config(config, device)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def _update_config(self, config, device):
        cyberark_queries = False
        # initial run to check for cyberark queries
        if not hasattr(config, 'cyberark_queries'):
            for attr, value in vars(config).items():
                if isinstance(value, basestring) and value.startswith(self.cyberark_query):
                    self.manager.add(device, attr, value.strip())
                    cyberark_queries = True
            config.cyberark_queries = cyberark_queries

        # config is already checked and it didn't have cyberark queries, skip it
        if config.cyberark_queries is False:
            defer.returnValue(None)
        yield self.manager.update(device)
        props_to_update = self.manager.get_props(device)
        for obj in props_to_update:
            if obj.result is None:
                raise Exception('CyberArk query is not updated.')
            setattr(config, obj.zprop, str(obj.result))
        defer.returnValue(None)


class CyberArkManager(object):
    def __init__(self, url, port, cert_path, cache_ttl, test_mode):
        self.url = url
        self.cert_path = cert_path
        self.port = port
        self.cache = ExpiringCache(int(cache_ttl))
        self.long_lived_cache = ExpiringCache(int(cache_ttl) * LONG_LIVE_CACHE_MULTIPLIER)
        self.properties = {}
        self.options = self.load_certificates()
        self._eventService = zope.component.queryUtility(IEventService)
        self.test_mode = test_mode

    def load_certificates(self):
        hostname = urlparse.urlsplit(self.url).netloc
        authority = ssl.Certificate.loadPEM(
            FilePath(os.path.join(self.cert_path, 'RootCA.crt')).getContent())
        client_cert = FilePath(os.path.join(self.cert_path, 'client.crt')).getContent()
        client_key = FilePath(os.path.join(self.cert_path, 'client.pem')).getContent()
        client_certificate = ssl.PrivateCertificate.loadPEM(client_cert + client_key)
        return ssl.optionsForClientTLS(hostname, authority, client_certificate)

    def sendEvent(self, evt):
        self._eventService.sendEvent(evt)

    def add(self, device, zprop, query):
        obj = self.properties.get((device, zprop))
        if obj is None:
            self.properties[(device, zprop)] = CyberArkProperty(device, zprop, query, self)

    def get_props(self, device_id):
        props = []
        for key, obj in self.properties.items():
            device, zprop = key
            if device == device_id:
                props.append(obj)
        return props

    @defer.inlineCallbacks
    def update(self, device):
        props = self.get_props(device)
        for obj in props:
            yield obj.update()
        defer.returnValue(None)


class CyberArkProperty(object):
    def __init__(self, device, zprop, query, manager):
        self.device = device
        self.zprop = zprop
        self.query = query
        self.manager = manager
        self._request_d = None
        self.switch = True

    @defer.inlineCallbacks
    def update(self):
        if self.result_in_cache():
            defer.returnValue(None)

        log.debug("Cache is empty, making request for device: %s", self.device)
        # wait for previous request to finish and re-check the cache
        if self._request_d and not self._request_d.called:
            yield self._request_d
            if self.result_in_cache():
                defer.returnValue(None)

        self._request_d = self._request(self.query)
        response = yield self._request_d
        log.debug('Request was successful')
        if response:
            self.result = response
            self.manager.cache.set((self.query, self.zprop), response)
            self.manager.long_lived_cache.set((self.query, self.zprop), response)

        defer.returnValue(None)

    def result_in_cache(self):
        self.result = self.manager.cache.get((self.query, self.zprop))
        if self.result is not None:
            log.debug("Get cached value for %s on %s" % (self.zprop, self.device))
            return True
        return False

    @defer.inlineCallbacks
    def _request(self, query):
        agent = client.Agent(reactor, contextFactory=MyPolicy(self.manager.options))
        parts = urlparse.urlsplit(self.manager.url)
        qp = query.split("/")
        qp = qp[1:] if not qp[0] else qp
        pp = parts.path.split("/")
        pp = pp[1:] if not pp[0] else pp
        url = "%s://%s:%s/%s" % (
            parts.scheme,
            parts.netloc,
            str(self.manager.port),
            "/".join(pp + qp)
        )
        log.debug('Request url: %s', url)
        test_mode = bool(distutils.util.strtobool(self.manager.test_mode))
        log.debug('CyberArk test mode %s', test_mode)
        if test_mode:
            delay = 1
            log.debug('Delay for %s sec', delay)
            yield sleep(delay)
            result = query.rsplit('=')[-1]
            # if self.switch:
            #     result = query.rsplit('=')[-1]
            #     self.switch = False
            # else:
            #     result = "test_value"
            #     self.switch = True
            defer.returnValue(result)

        request = agent.request('GET', bytes(url), None, None)
        request.addCallback(self.cbRequest)
        request.addErrback(self.cbError)
        result = yield request
        defer.returnValue(result)

    def cbRequest(self, response):
        finished = defer.Deferred()
        finished.addCallback(self.handle_result)
        response.deliverBody(DataReceiver(finished))
        self.manager.sendEvent(dict(
            device=self.device,
            summary="Successful CyberArk collection.",
            severity=Event.Clear,
            eventClass='/Status',
            eventKey='cyberark'))
        return finished

    def handle_result(self, response):
        return response

    def cbError(self, error):
        if isinstance(error, Failure):
            message = error.getErrorMessage()
        else:
            message = str(error)
        log.error('An error occurs during request: %s' % message)
        log.warn('Trying to get a value from long-lived cache.')
        response = self.manager.long_lived_cache.get((self.query, self.zprop))
        if response:
            log.debug('Get value from long-lived cache for: %s on device: %s', self.zprop, self.device)
            self.result = response
            self.manager.cache.set((self.query, self.zprop), response)
        else:
            log.error('Faled to get value from long-lived cache.')

        summary = "Error in CyberArk API request for %s: %s" % (self.zprop, message)
        self.manager.sendEvent(dict(
            device=self.device,
            summary=summary,
            severity=Event.Error,
            eventClass='/Status',
            eventKey='cyberark'))


class MyPolicy(client.BrowserLikePolicyForHTTPS):

    def __init__(self, options, *args, **kwargs):
        super(MyPolicy, self).__init__(*args, **kwargs)
        self.options = options

    def creatorForNetloc(self, hostname, port):
        return self.options


class DataReceiver(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.response = ""

    def dataReceived(self, bytes):
        response = json.loads(bytes)
        self.response = response.get('Content')

    def connectionLost(self, reason):
        self.finished.callback(self.response)
