##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import requests
import urlparse

from zope.component.factory import Factory
from zope.interface import implements

from .fact import serialize_facts
from .interfaces import IZingConnectorClient, IZingConnectorProxy
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration


logging.basicConfig()
log = logging.getLogger("zen.zing")

GLOBAL_ZING_CONNECTOR_URL = "zing-connector-url"
GLOBAL_ZING_CONNECTOR_ENDPOINT = "zing-connector-endpoint"
GLOBAL_ZING_CONNECTOR_TIMEOUT = "zing-connector-timeout"
DEFAULT_HOST = "http://localhost:9237"
DEFAULT_ENDPOINT = "/api/model/ingest"
PING_ENDPOINT = "/_admin/ping"
DEFAULT_TIMEOUT = 5


class ZingConnectorConfig(object):
    def __init__(self, host=None, endpoint=None, timeout=None):
        host = host or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_URL) or DEFAULT_HOST
        endpoint = endpoint or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_ENDPOINT) or DEFAULT_ENDPOINT
        timeout = timeout or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_TIMEOUT) or DEFAULT_TIMEOUT
        self.facts_url = urlparse.urljoin(host, endpoint)
        self.ping_url = urlparse.urljoin(host, PING_ENDPOINT)
        self.timeout = timeout


class ZingConnectorClient(object):
    implements(IZingConnectorClient)

    def __init__(self, config=None):
        if config is None:
            config = ZingConnectorConfig()
        self.config = config
        self.session = requests.Session()

    @property
    def facts_url(self):
        return self.config.facts_url

    @property
    def ping_url(self):
        return self.config.ping_url

    @property
    def client_timeout(self):
        return self.config.timeout

    def _send_facts(self, facts, already_serialized=False):
        resp_code = -1
        try:
            if not facts: # nothing to send
                return 200
            if already_serialized:
                serialized = facts
            else:
                serialized = serialize_facts(facts)
            resp = self.session.put(self.facts_url, data=serialized, timeout=self.client_timeout)
            resp_code = resp.status_code
        except Exception as e:
            log.exception("Unable to send facts. zing-connector URL: {}. Exception {}".format(self.facts_url, e))
        return resp_code

    def _send_one_by_one(self, facts):
        failed = 0
        for fact in facts:
            serialized = serialize_facts( [fact] )
            resp_code = self._send_facts(serialized, already_serialized=True)
            if resp_code != 200:
                failed += 1
                log.warn("Error sending fact: {}".format(serialized))
        log.warn("{} out of {} facts were not processed.".format(failed, len(facts)))

    def send_facts(self, facts):
        resp_code = self._send_facts(facts)
        if resp_code != 200:
            log.error("Error sending datamaps: zing-connector returned an unexpected response code ({})".format(resp_code))
            if resp_code == 500:
                log.info("Sending facts one by one to minimize data loss")
                self._send_one_by_one(facts)
        return resp_code == 200

    def ping(self):
        resp_code = -1
        try:
            resp = self.session.get(self.ping_url, timeout=0.2)
            resp_code = resp.status_code
        except Exception as e:
            log.debug("Zing connector is unavailable")
        return resp_code == 200


class ZingConnectorProxy(object):
    """ This class provides a ZingConnectorClient per zope thread """
    implements(IZingConnectorProxy)

    def __init__(self, context):
        self.context = context
        self.client = self.get_client(self.context)

    def get_client(self, context):
        """
        Retrieves/creates the zing connector client for the zope thread that is trying to access zing connector
        """
        zodb_conn = getattr(self.context, "_p_jar", None)

        client = None
        # context is not a persistent object. Create a temp client in a volatile variable.
        # Volatile variables are not shared across threads, so each thread will have its own client
        #
        if zodb_conn is None:
            if not hasattr(self, "_v_temp_zing_connector_client"):
                self._v_temp_zing_connector_client = ZingConnectorClient()
            client = self._v_temp_zing_connector_client
        else:
            #
            # context is a persistent object. Create/retrieve the client
            # from the zodb connection object. We store the client in the zodb
            # connection object so we are certain that each zope thread has its own
            client = getattr(zodb_conn, 'zing_connector_client', None)
            if client is None:
                setattr(zodb_conn, 'zing_connector_client', ZingConnectorClient())
                client = zodb_conn.zing_connector_client
        return client

    def send_facts(self, facts):
        return self.client.send_facts(facts)

    def ping(self):
        return self.client.ping()

CLIENT_FACTORY = Factory(ZingConnectorClient)

