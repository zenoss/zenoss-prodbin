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
    def send_facts(self, facts):
        """
        Sends facts to zing-connector. Returns boolean indicating if the request succeeded
        """

    def ping(self):
        """
        Checks the connection to zing-connector is healthy
        """


class IZingConnectorProxy(IZingConnectorClient):
    """ Marker Interface to register an utility for the zing connector proxy """


class IZingDatamapHandler(Interface):
    """ Marker Interface to register an utility to process datamaps """