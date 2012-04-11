###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from celery.loaders.base import BaseLoader
from zenoss.protocols.amqpconfig import AMQPConfig
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration


class ZenossLoader(BaseLoader):

    override_backends = {
        'zodb': 'Products.ZenUtils.celeryintegration.ZODBBackend'
    }

    def on_worker_process_init(self):
        """
        Clear out connections and dbs
        """
        self.app.backend.reset()

    def read_configuration(self):
        """
        Build a Celery configuration dictionary using global.conf.
        """
        globalCfg = getGlobalConfiguration()
        amqpCfg = AMQPConfig()
        amqpCfg.update(globalCfg)
        self.configured = True
        return {

            # AMQP connection
            'BROKER_HOST': amqpCfg.host,
            'BROKER_PORT': amqpCfg.port,
            'BROKER_USER': amqpCfg.user,
            'BROKER_PASSWORD': amqpCfg.password,
            'BROKER_VHOST': amqpCfg.vhost,
            'BROKER_USE_SSL': amqpCfg.usessl,

            # Cache settings
            'CELERY_CACHE_BACKEND': 'memcached://' + getattr(amqpCfg, 'zodb_cacheservers',
                                                             '127.0.0.1:11211'),

            # Result backend settings
            'CELERY_RESULT_BACKEND': 'zodb',

            # Workers settings
            # Default to 1 job per worker process
            'CELERYD_MAX_TASKS_PER_CHILD': globalCfg.get('max-jobs-per-job-worker', 1)

        }

