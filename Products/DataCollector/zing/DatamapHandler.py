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
ZING_CONNECTOR_DATAMAP_ENDPOINT = "/api/model/ingest"

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
            self._send_facts(batch)

    def _send_facts(self, facts):
        try:
            if not facts: # nothing to send
                return
            serialized = serialize_facts(facts)
            resp = self.session.put(self.zing_connector_url, data=serialized)
            if resp.status_code != 200:
                log.error("Error sending datamaps: zing-connector returned an unexpected response code ({})".format(resp.status_code))
                log.debug("Datamaps for which zing-connector returned unexpected response: {}".format(serialized))
        except Exception:
            log.exception("Unable to process datamap. zing-connector URL: {}".format(self.zing_connector_url))

