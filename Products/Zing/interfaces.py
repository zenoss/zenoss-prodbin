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

    def send_fact_generator_in_batches(self, fact_gen, batch_size):
        """
        Sends facts given by the passed generator to zing-connector. Returns boolean indicating if the requests succeeded
        """

    def ping(self):
        """
        Checks the connection to zing-connector is healthy
        """


class IZingConnectorProxy(IZingConnectorClient):
    """ Marker Interface to register an utility for the zing connector proxy """


class IZingDatamapHandler(Interface):
    """ Marker Interface to register an utility to process datamaps """