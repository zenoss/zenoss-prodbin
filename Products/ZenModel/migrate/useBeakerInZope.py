##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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


class UseBeakerInZope(Migrate.Step):
    """
    Use Beaker in Zope
    """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        beaker_config_text = """
<product-config beaker>
    cache.type              ext:memcached
    cache.url               127.0.0.1:11211
    cache.data_dir          /tmp/cache/data
    cache.lock_dir          /tmp/cache/lock
    cache.regions           short, long
    cache.short.expire      60
    cache.long.expire       3600

    session.type            ext:memcached
    session.url             127.0.0.1:11211
    session.data_dir        /tmp/sessions/data
    session.lock_dir        /tmp/sessions/lock
    session.key             beaker.session
    session.secret          supersecret
</product-config>
"""

        zopes_and_zauths = filter(lambda s: s.name in ["zope", "zauth"], ctx.services)
        for z in zopes_and_zauths:
            for configfile in filter(lambda f: f.name == '/opt/zenoss/etc/zope.conf', z.configFiles):
                if '<product-config beaker>' in configfile.content:
                    continue
                configfile.content += beaker_config_text
        ctx.commit()

UseBeakerInZope()

