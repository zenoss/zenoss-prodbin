##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute


class IZingConnectorClient(Interface):
    """ """
    def send_facts(self, facts, ping):
        """
        Sends a list of facts to zing-connector. Returns boolean indicating if the request succeeded
        """

    def send_facts_in_batches(self, facts, batch_size):
        """
        Sends a list of facts to zing-connector in batches. Returns boolean indicating if the requests succeeded
        """

    def send_fact_generator_in_batches(self, fact_gen, batch_size, external_log=None):
        """
        Sends facts given by the passed generator to zing-connector. Returns boolean indicating if the requests succeeded
        """

    def ping(self):
        """
        Checks the connection to zing-connector is healthy
        """


class IZingConnectorProxy(IZingConnectorClient):
    """ Marker Interface to register an utility for the zing connector proxy """


class IZingFactGenerator(Interface):
    """ """
    def generate_facts(self, zing_tx_state):
        """
        Build a generator of facts from the information available in
        zing_tx_state (ZingTxState)
        """

class IZingDatamapHandler(IZingFactGenerator):
    """ Marker Interface to register an utility to process datamaps """


class IZingObjectUpdateHandler(IZingFactGenerator):
    """ Marker Interface to register an utility to process object updates """


class IImpactRelationshipsFactProvider(Interface):
    """  """
    def impact_relationships_fact(uuid):
        """
        Return an impact relationship fact for the passed uuid, if the object
        does not belong in the impact graph it returns None
        """


class IObjectMapContextProvider(Interface):
    """Interface for providers of ObjectMapContext data."""

    def __init__(self, obj):
        """Initialize adapter with obj."""

    def get_dimensions(self, obj):
        """Return dict of dimensions for obj."""

    def get_metadata(self, obj):
        """Return dict of metadata for obj."""
