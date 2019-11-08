##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Add the KEYPROXY_SESSION_SVC environment variable to zing-api-proxy
    and add an empty gcp.loadbalancing.gke-ilb.frontend variable to zproxy's Context
"""
import logging
import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")

sm.require("1.1.11")

class AddSessionSvcToApiProxy(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def _getService(self, ctx, name):
        return next(
            iter(filter(lambda s: s.name == name, ctx.services)), None
        )

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping")
            return

        env_entry = "KEYPROXY_SESSION_SVC={{(getContext . \"gcp.loadbalancing.gke-ilb.frontend\")}}"
        context_key = "gcp.loadbalancing.gke-ilb.frontend"

        commit = False
        zproxy = ctx.getTopService()
        if not zproxy:
            log.info("Couldn't find the top level service, skipping")
            return

        if not zproxy.name == 'Zenoss.cse':
            log.info("Skipping migration in non-cse install")
            return

        log.info("Top-level service is '{}'.".format(zproxy.name))

        if not context_key in zproxy.context:
            zproxy.context[context_key] = ""
            commit = True

        apiProxy = self._getService(ctx, "zing-api-proxy")

        if apiProxy:
            if env_entry not in apiProxy.environment:
                apiProxy.environment.append(env_entry)
                commit = True
        else:
            log.warn("Could not find zing-api-proxy service")

        if commit:
            ctx.commit()


AddSessionSvcToApiProxy()
