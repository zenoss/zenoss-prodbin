##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from Products.Jobber.task import requires, Abortable, DMD
from Products.Jobber.zenjobs import app

from .fact import device_organizer_info_fact
from .interfaces import IZingConnectorProxy


@app.task(
    bind=True,
    base=requires(Abortable, DMD),
    name="zen.zenjobs.zing.send_organizers",
    summary="Send organizer facts to Zing",
    ignore_result=False,
)
def send_organizers(self):
    facts = {}
    for root_name in ("Devices", "Groups", "Locations"):
        root = getattr(self.dmd, root_name, None)
        if root is None:
            continue
        for organizer_name in root.getOrganizerNames():
            organizer_name = organizer_name.lstrip("/")
            if not organizer_name:
                continue
            organizer = root.unrestrictedTraverse(organizer_name)
            uuid = organizer.getUUID()
            if uuid in facts:
                continue
            facts[uuid] = device_organizer_info_fact(organizer)
    zing_connector = IZingConnectorProxy(self.dmd)
    if not zing_connector.ping():
        self.log.error(
            "Error processing facts: zing-connector cant be reached"
        )
        return
    zing_connector.send_facts_in_batches(facts.values())
    self.log.info("Sent %d organizer facts", len(facts))
