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

from . import constants


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

        This configuration may be overwritten or augmented later by a daemon.
        """
        globalCfg = getGlobalConfiguration()
        amqpCfg = AMQPConfig()
        amqpCfg.update(globalCfg)

        config = {

            #############
            # TRANSPORT #
            #############

            constants.BROKER_HOST: amqpCfg.host,
            constants.BROKER_PORT: amqpCfg.port,
            constants.BROKER_USER: amqpCfg.user,
            constants.BROKER_PASSWORD: amqpCfg.password,
            constants.BROKER_VHOST: amqpCfg.vhost,
            constants.BROKER_USE_SSL: amqpCfg.usessl,

            ################
            # RESULT STORE #
            ################

            constants.RESULT_BACKEND: 'zodb',

            ###########
            # WORKERS #
            ###########

            # Default to 1 job per worker process
            constants.MAX_TASKS_PER_PROCESS: 1,
            # 2 job workers
            constants.NUM_WORKERS: 2,

            ###########
            # LOGGING #
            ###########

            # Handle logging ourselves
            constants.USE_CELERY_LOGGING: False,
            # Log file formats
            constants.LOG_FORMAT: "%(asctime)s %(levelname)s %(name)s: %(message)s",
            constants.TASK_LOG_FORMAT: "%(asctime)s %(levelname)s zen.Job: %(message)s",
            # Level at which stdout should be logged
            constants.STDOUT_LOG_LEVEL: 'INFO'
        }

        return config

