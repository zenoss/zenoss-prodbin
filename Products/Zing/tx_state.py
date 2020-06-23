##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import transaction
from itertools import chain

from zope.component import createObject, getUtility
from zope.component.interfaces import ComponentLookupError

from .interfaces import IZingConnectorProxy, IImpactRelationshipsFactProvider

logging.basicConfig()
log = logging.getLogger("zen.zing.transaction")


class ZingTxState(object):
    """
    All relevant object updates within a transaction are buffered in this data structure
    in the transaction object. Once the tx successfully commits, facts will be generated
    and sent to zing-connector
    """
    def __init__(self):
        # updated by zenhub during apply datamaps (ZingDatamapHandler)
        #
        self.datamaps = []
        self.datamaps_contexts = {}

        # updated by model_catalog IndexingEvent machinerie (ZingObjectUpdateHandler)
        #
        self.need_organizers_fact = {}  # contextUUIDs:Fact that need an organizers fact
        self.need_device_info_fact = {} # contextUUIDs:Fact that need a device info fact
        self.need_device_organizer_info_fact = {}
        self.need_deletion_fact = {}    # contextUUIDs:Fact that need a deletion fact

        # sets containing the uuids for which we have already sent a type of fact
        # to avoid sending the same fact more than once
        self.already_generated_organizer_facts = set()
        self.already_generated_device_info_facts = set()
        self.already_generated_device_organizer_info_facts = set()
        self.already_generated_impact_facts = set()

        self.impact_installed = False
        try:
            getUtility(IImpactRelationshipsFactProvider)
            self.impact_installed = True
        except ComponentLookupError:
            pass

    def is_there_datamap_updates(self):
        return len(self.datamaps) > 0

    def is_there_object_updates(self):
        return any((
            len(self.need_organizers_fact) > 0,
            len(self.need_device_info_fact) > 0,
            len(self.need_device_organizer_info_fact) > 0,
            len(self.need_deletion_fact) > 0,
        ))


def get_zing_tx_state():
    current_tx = transaction.get()
    return getattr(current_tx, ZingTxStateManager.TX_DATA_FIELD_NAME, None)


class ZingTxStateManager(object):

    TX_DATA_FIELD_NAME = "zing_tx_state"

    def get_zing_tx_state(self, context):
        """
        Get the ZingTxState object for the current transaction.
        If it doesnt exists, create one.
        """
        zing_tx_state = None
        current_tx = transaction.get()
        zing_tx_state = getattr(current_tx, self.TX_DATA_FIELD_NAME, None)
        if not zing_tx_state:
            zing_tx_state = ZingTxState()
            setattr(current_tx, self.TX_DATA_FIELD_NAME, zing_tx_state)
            current_tx.addAfterCommitHook(self.process_facts, args=(zing_tx_state, context))
            log.debug("ZingTxStateManager AfterCommitHook added. State added to current transaction.")
        return zing_tx_state

    def _generate_facts(self, context, zing_connector, zing_tx_state):
        fact_generators = []
        if zing_tx_state.is_there_datamap_updates():
            # process datamaps
            datamap_handler = createObject("ZingDatamapHandler", context)
            fact_generators.append(datamap_handler.generate_facts(zing_tx_state))
        if zing_tx_state.is_there_object_updates():
            # process object updates
            object_updates_handler = createObject("ZingObjectUpdateHandler", context)
            fact_generators.append(object_updates_handler.generate_facts(zing_tx_state))
        return fact_generators

    def process_facts(self, tx_success, zing_tx_state, context):
        """
        this method is an addAfterCommitHook and is automatically called by the transaction manager
        """
        if not tx_success:
            return
        try:
            zing_connector = IZingConnectorProxy(context)
            if not zing_connector.ping():
                log.error("Error processing facts: zing-connector cant be reached")
                return
            fact_generators = self._generate_facts(context, zing_connector, zing_tx_state)
            if fact_generators:
                zing_connector.send_fact_generator_in_batches(fact_gen=chain(*fact_generators))
        except Exception:
            log.exception("Exception processing facts for zing-connector")


