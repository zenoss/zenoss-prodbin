##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import httplib
import requests
import threading
import time
import urlparse
import json

from zope.component import createObject
from zope.component.factory import Factory
from zope.interface import implementer

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from .fact import serialize_facts
from .interfaces import IZingConnectorClient, IZingConnectorProxy

log = logging.getLogger("zen.zing.zing-connector")

# Thread local storage for zing client
_zing = threading.local()

GLOBAL_ZING_CLIENT_NAME = "zing-connector-client"
GLOBAL_ZING_CONNECTOR_URL = "zing-connector-url"
GLOBAL_ZING_CONNECTOR_ENDPOINT = "zing-connector-endpoint"
GLOBAL_ZING_CONNECTOR_TIMEOUT = "zing-connector-timeout"

DEFAULT_CLIENT = "ZingConnectorClient"
DEFAULT_HOST = "http://localhost:9237"
DEFAULT_ENDPOINT = "/api/model/ingest"
DEFAULT_TIMEOUT = 5
DEFAULT_BATCH_SIZE = 1000


class ZingConnectorConfig(object):
    def __init__(self, host=None, endpoint=None, timeout=None):
        host = (
            host
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_URL)
            or DEFAULT_HOST
        )
        endpoint = (
            endpoint
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_ENDPOINT)
            or DEFAULT_ENDPOINT
        )
        self.facts_url = urlparse.urljoin(host, endpoint)

        timeout = (
            timeout
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_TIMEOUT)
            or DEFAULT_TIMEOUT
        )

        if type(timeout) is not float:
            try:
                timeout = float(timeout)
            except Exception:
                log.error("could not coerce timeout to float: %s", timeout)

        self.timeout = timeout

        # admin port exists no longer
        self.ping_url = self.facts_url


def _getZingConnectorClient():
    client_name = (
        getGlobalConfiguration().get(GLOBAL_ZING_CLIENT_NAME)
        or DEFAULT_CLIENT
    )
    return createObject(client_name)


@implementer(IZingConnectorClient)
class NullZingClient(object):
    """Implements the IZingConnectorClient interface, but no I/O.
    """

    def __init__(self, config=None):
        if config is None:
            config = ZingConnectorConfig()
        self.config = config

    @property
    def facts_url(self):
        return self.config.facts_url

    @property
    def ping_url(self):
        return self.config.ping_url

    @property
    def client_timeout(self):
        return self.config.timeout

    def send_facts(self, facts, ping):
        return True

    def send_facts_in_batches(self, facts, batch_size):
        return True

    def send_fact_generator_in_batches(
        self, fact_gen, batch_size, external_log=None
    ):
        # Exercise the generator; the facts could be lazily created.
        for f in fact_gen:
            pass
        return True

    def ping(self):
        return True

def _has_errors(resp):
    try:
        json_content = json.loads(resp.content)
        errors = json_content.get("errors", [])
        return len(errors) > 0
    except Exception as e:
        log.error("response has errors: %s, exception: %s", resp.content, e)
    return False

def _has_errors(resp):
    try:
        json_content = json.loads(resp.content)
        errors = json_content.get("errors", [])
        return len(errors) > 0
    except Exception as e:
        log.error("response has errors: %s, exception: %s", resp.content, e)
    return False


@implementer(IZingConnectorClient)
class ZingConnectorClient(object):

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
            if not facts:  # nothing to send
                return httplib.OK
            if already_serialized:
                serialized = facts
            else:
                serialized = serialize_facts(facts)
            resp = self.session.put(
                self.facts_url, data=serialized, timeout=self.client_timeout
            )
            if _has_errors(resp):
                return httplib.INTERNAL_SERVER_ERROR
            resp_code = resp.status_code
        except Exception as e:
            log.exception(
                "Unable to send facts  URL=%s error=%s", self.facts_url, e,
            )
        return resp_code

    def _send_one_by_one(self, facts):
        failed = 0
        for fact in facts:
            serialized = serialize_facts([fact])
            resp_code = self._send_facts(serialized, already_serialized=True)
            if resp_code != httplib.OK:
                failed += 1
                log.warn("Error sending fact: %s", serialized)
        log.warn("%s out of %s facts were not processed.", failed, len(facts))
        return failed == 0

    def log_zing_connector_not_reachable(self, custom_msg=""):
        msg = "zing-connector is not available"
        if custom_msg:
            msg = "{}. {}".format(custom_msg, msg)
        log.error(msg)

    def send_facts(self, facts, ping=True):
        """
        @param facts: list of facts to send to zing connector
        @param ping: boolean indicating if it should ping zing-connector
            before sending the facts.
        @return: boolean indicating if all facts were successfully sent
        """
        if ping and not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        resp_code = self._send_facts(facts)
        if resp_code != httplib.OK:
            log.error(
                "Error sending datamaps: zing-connector returned an "
                "unexpected response code (%s)", resp_code,
            )
            if resp_code == httplib.INTERNAL_SERVER_ERROR:
                log.info("Sending facts one by one to minimize data loss")
                return self._send_one_by_one(facts)
        return resp_code == httplib.OK

    def send_facts_in_batches(self, facts, batch_size=DEFAULT_BATCH_SIZE):
        """
        @param facts: list of facts to send to zing connector
        @param batch_size: doh
        """
        log.debug(
            "Sending %s facts in batches of %s.", len(facts), batch_size,
        )
        success = True
        if not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        while facts:
            batch = facts[:batch_size]
            del facts[:batch_size]
            success = success and self.zing_connector.send_facts(
                batch, ping=False
            )
        return bool(success)

    def send_fact_generator_in_batches(
        self, fact_gen, batch_size=DEFAULT_BATCH_SIZE, external_log=None
    ):
        """
        @param fact_gen: generator of facts to send to zing connector
        @param batch_size: doh
        """
        if external_log is None:
            external_log = log
        external_log.debug(
            "Sending facts to zing-connector in batches of %s", batch_size,
        )
        ts = time.time()
        count = 0
        if not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        success = True
        batch = []
        for f in fact_gen:
            count += 1
            batch.append(f)
            if len(batch) % batch_size == 0:
                success = success and self.send_facts(batch, ping=False)
                batch = []
        if batch:
            success = success and self.send_facts(batch, ping=False)
        if count > 0:
            elapsed = time.time() - ts
            external_log.debug(
                "send_fact_generator_in_batches sent %s facts in %s seconds",
                count,
                elapsed,
            )
        return bool(success)

    def ping(self):
        resp_code = -1
        try:
            resp = self.session.get(self.ping_url, timeout=0.2)
            resp_code = resp.status_code
        except Exception:
            log.debug("Zing connector is unavailable at %s", self.ping_url)
        # We expect zing-connector to return 501 (NOT IMPLEMENTED) for
        # ping requests.
        return resp_code == httplib.NOT_IMPLEMENTED


@implementer(IZingConnectorProxy)
class ZingConnectorProxy(object):
    """This class provides a ZingConnectorClient per zope thread.
    """

    @staticmethod
    def get_client():
        """
        Retrieves/creates the zing connector client for the zope thread that
        is trying to access zing connector.
        """
        global _zing
        client = getattr(_zing, "client", None)
        if client is None:
            client = _getZingConnectorClient()
            _zing.client = client
        return client

    def __init__(self, context):
        self.client = self.get_client()

    def send_facts(self, facts):
        return self.client.send_facts(facts)

    def send_facts_in_batches(self, facts, batch_size=DEFAULT_BATCH_SIZE):
        return self.client.send_facts_in_batches(facts, batch_size)

    def send_fact_generator_in_batches(
        self, fact_gen, batch_size=DEFAULT_BATCH_SIZE, external_log=None
    ):
        return self.client.send_fact_generator_in_batches(
            fact_gen, batch_size, external_log
        )

    def ping(self):
        return self.client.ping()


CLIENT_FACTORY = Factory(ZingConnectorClient)
NULL_CLIENT_FACTORY = Factory(NullZingClient)
