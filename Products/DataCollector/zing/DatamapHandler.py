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
import transaction

from Products.DataCollector.zing.fact import FactContext, Fact, facts_from_datamap, serialize_facts
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration


GLOBAL_ZING_CONNECTOR_URL = "zing-connector-url"
GLOBAL_ZING_CONNECTOR_TIMEOUT = "zing-connector-timeout"
ZING_CONNECTOR_DATAMAP_ENDPOINT = "/api/model/ingest"
DEFAULT_TIMEOUT = 2

logging.basicConfig()
log = logging.getLogger("zen.DatamapHandler")


TX_DATA_FIELD_NAME = "zing_state"


class ZingTxState(object):
    """
    All datamaps processed within a transaction are buffered in this data structure
    in the transaction object. Once the tx successfully commits, datamaps will be
    serialized and sent to zing-connector
    """
    def __init__(self):
        self.datamaps = []
        self.contexts = {}
        self.devices_fact = {} # dummy fact per processed device


class ZingDatamapHandler(object):

    def __init__(self):
        self.session = requests.Session()
        self.zing_connector_url = self.get_zing_connector_url()
        self.zing_connector_timeout = self.get_zing_connector_timeout()
        msg = "Zenhub{}configured to send datamps to zing-connector. {}"
        if not self.zing_connector_url:
            log.warn(msg.format(" NOT ", ""))
        else:
            url_msg = "URL: {}".format(self.zing_connector_url)
            log.info(msg.format(" ", url_msg))

    def get_zing_connector_url(self):
        zing_connector_host = getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_URL)
        if zing_connector_host:
            return urlparse.urljoin(zing_connector_host, ZING_CONNECTOR_DATAMAP_ENDPOINT)

    def get_zing_connector_timeout(self):
        timeout = getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_TIMEOUT)
        if not timeout:
            timeout = DEFAULT_TIMEOUT
        return timeout

    def _get_zing_tx_state(self):
        """
        Get the ZingTxState object for the current transaction.
        If it doesnt exists, create it.
        """
        zing_tx_state = None
        current_tx = transaction.get()
        zing_tx_state = getattr(current_tx, TX_DATA_FIELD_NAME, None)
        if not zing_tx_state:
            zing_tx_state = ZingTxState()
            setattr(current_tx, TX_DATA_FIELD_NAME, zing_tx_state)
            current_tx.addAfterCommitHook(self.process_datamaps, args=(zing_tx_state,))
            log.info("Zing AfterCommitHook added. Zing state added to current transaction.")
        return zing_tx_state

    def add_datamap(self, device, datamap):
        """ adds the datamap to the ZingTxState in the current tx"""
        if self.zing_connector_url: # dont bother to store maps if the url no set
            zing_state = self._get_zing_tx_state()
            zing_state.datamaps.append( (device, datamap) )
            # Create a dummy fact for the device to make sure Zing has one for each device
            device_uid = device.getPrimaryId()
            if device_uid not in zing_state.devices_fact:
                zing_state.devices_fact[device_uid] = Fact.from_device(device)

    def add_context(self, objmap, ctx):
        """ adds the context to the ZingTxState in the current tx """
        if self.zing_connector_url: # dont bother to store if the url no set
            zing_state = self._get_zing_tx_state()
            zing_state.contexts[objmap] = FactContext(ctx)

    def process_datamaps(self, tx_success, zing_state):
        """
        This is called on the AfterCommitHook
        Send the datamaps to zing-connector if the tx succeeded
        """
        if not tx_success or not self.zing_connector_url:
            return
        try:
            log.debug("Sending {} datamaps to zing-connector.".format(len(zing_state.datamaps)))
            facts = []
            for device, datamap in zing_state.datamaps:
                dm_facts = facts_from_datamap(device, datamap, zing_state.contexts)
                if dm_facts:
                    facts.extend(dm_facts)
            # add dummy facts for the processed devices
            device_facts = zing_state.devices_fact.values()
            if device_facts:
                facts.extend(device_facts)
            self._send_facts_in_batches(facts)
        except Exception as ex:
            log.warn("Exception sending datamaps to zing-connector. {}".format(ex))

    def _send_facts_in_batches(self, facts, batch_size=500):
        log.info("Sending {} facts to zing-connector.".format(len(facts)))
        while facts:
            batch = facts[:batch_size]
            del facts[:batch_size]
            self.send_facts(batch)

    def _send_facts(self, facts, already_serialized=False):
        resp_code = -1
        try:
            if not facts: # nothing to send
                return 200
            if already_serialized:
                serialized = facts
            else:
                serialized = serialize_facts(facts)
            resp = self.session.put(self.zing_connector_url, data=serialized, timeout=self.zing_connector_timeout)
            resp_code = resp.status_code
        except Exception as e:
            log.exception("Unable to send facts. zing-connector URL: {}. Exception {}".format(self.zing_connector_url, e))
        return resp_code

    def send_facts(self, facts):
        resp_code = self._send_facts(facts)
        if resp_code != 200:
            log.error("Error sending datamaps: zing-connector returned an unexpected response code ({})".format(resp_code))
            if resp_code == 500:
                log.info("Sending facts one by one to minimize data loss")
                self.send_one_by_one(facts)
        return resp_code == 200

    def send_one_by_one(self, facts):
        failed = 0
        for fact in facts:
            serialized = serialize_facts( [fact] )
            resp_code = self._send_facts(serialized, already_serialized=True)
            if resp_code != 200:
                failed += 1
                log.warn("Error sending fact: {}".format(serialized))
        log.warn("{} out of {} facts were not processed.".format(failed, len(facts)))


