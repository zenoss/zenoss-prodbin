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
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .fact import component_group_info_fact
from .interfaces import IZingConnectorProxy


@app.task(
    bind=True,
    base=requires(Abortable, DMD),
    name="zen.zenjobs.zing.send_component_groups",
    summary="Send component group facts to Zing",
    ignore_result=False,
)
def send_component_groups(self):
    facts = {}
    tool = IModelCatalogTool(self.dmd)
    results = tool.search({"meta_type": "ComponentGroup"})
    for cg in results:
        uuid = cg.getUUID()
        if uuid in facts:
            continue
        facts[uuid] = component_group_info_fact(cg)

    if not facts:
        self.log.info("No component groups found")
        return

    zing_connector = IZingConnectorProxy(self.dmd)
    if not zing_connector.ping():
        self.log.error(
            "Error processing facts: zing-connector cant be reached"
        )
        return
    zing_connector.send_facts_in_batches(facts.values())
    self.log.info("Sent %d component group facts", len(facts))
