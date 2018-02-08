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

from Products.DataCollector.zing.fact import serialize_datamap
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

GLOBAL_ZING_CONNECTOR_URL = "zing-connector-url"
ZING_CONNECTOR_DATAMAP_ENDPOINT = "/api/model/ingest"

log = logging.getLogger("zen.DatamapHandler")


class DatamapHandler(object):

    def __init__(self):
        self.session = requests.Session()

    def get_url(self):
        zing_connector_host = getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_URL)
        if zing_connector_host:
            return urlparse.urljoin(zing_connector_host, ZING_CONNECTOR_DATAMAP_ENDPOINT)

    def send_datamap(self, device, datamap, context):
        url = self.get_url()
        if not url:
            log.warn("zing-connector not configured, datamap not forwarded")
            return

        try:
            dm = serialize_datamap(device, datamap, context)
            if not dm:
                # nothing to send
                return

            resp = self.session.put(url, data=dm)
            if resp.status_code != 200:
                log.error("zing-connector returned an unexpected response " +
                          "code ({}) for datamap {}".format(resp.status_code, dm))
        except Exception:
            log.exception("Unable to process datamap")
