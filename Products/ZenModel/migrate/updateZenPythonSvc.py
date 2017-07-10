##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")

class UpdateZenPythonSvc(Migrate.Step):
    """
    Add resetValue and rateOption for datapoints
    """

    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zenpython_services = filter(lambda s: s.name == 'zenpython', ctx.services)
        log.info("Found %i services named 'zenpython'." % len(zenpython_services))

        # change the monitoring profile
        for svc in zenpython_services:
            m_prof = svc.monitoringProfile

            # the graph config part
            commit = False
            for g_conf in m_prof.graphConfigs:
                for p in g_conf.datapoints:
                    if p.rate == True and ( not p.rateOptions ):
                        commit = True
                        p.rateOptions = {
                                "counter": True,
                                "resetThreshold": 1048576000
                                }
                        log.info("{0}.rateOptions set to {1}".format(p.name, p.rateOptions))

            # the metric part
            for m_conf in m_prof.metricConfigs:
                metrics = m_conf.metrics
                for m in metrics:
                    if m.counter == True and m.resetValue == 0:
                        commit = True
                        m.resetValue = 1048576000
                        log.info("{0}.resetValue set to {1}".format(m.name, m.resetValue))

        # commit if anything changed
        if commit:
            ctx.commit()

UpdateZenPythonSvc()
