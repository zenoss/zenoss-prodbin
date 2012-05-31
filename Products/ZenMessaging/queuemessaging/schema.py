###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import json
import logging
from zope.component import getUtility
from zenoss.protocols.amqp import Publisher as BlockingPublisher
from zenoss.protocols.queueschema import substitute_replacements, MissingReplacementException
from zenoss.protocols.queueschema import Schema
from zenoss.protocols.data.queueschema import SCHEMA
from zenoss.protocols.interfaces import IQueueSchema, IAMQPConnectionInfo

import Globals
from Products.ZenUtils.PkgResources import pkg_resources

def _loadQjs(pack_path):
    """
    Load one or more queue schema files from a ZenPack.
    They should live in PACK/protocols/*.qjs.
    """
    schemas = []
    protocols_path = os.path.join(pack_path, 'protocols')
    if not os.path.isdir(protocols_path):
        return schemas

    for fname in os.listdir(protocols_path):
        if fname.endswith('.qjs'):
            fullpath = os.path.abspath(os.path.join(protocols_path, fname))
            if not os.path.isfile(fullpath):
                continue
            try:
                with open(fullpath) as f:
                    schemas.append(json.load(f))
            except:
                logging.basicConfig()
                log = logging.getLogger('zen.ZenMessaging')
                log.exception("Failed to load qjs schema from ZenPack: %s", fullpath)
                raise

    return schemas

def _getZenPackSchemas():
    schemas = []
    for zpkg in pkg_resources.iter_entry_points('zenoss.zenpacks'):
        try:
            pkg_path = zpkg.load().__path__[0]

            # Load any queue schema files
            schemas.extend(_loadQjs(pkg_path))

        except Exception, e:
            # This messes up logging a bit, but if we need to report
            # an error, this saves hours of trying to find out what's going on
            logging.basicConfig()
            log = logging.getLogger('zen.ZenMessaging')
            log.exception("Error encountered while processing %s", zpkg.module_name)

    return schemas

def _loadZenossQueueSchemas():
    schemas = [SCHEMA] # Load the compiled schema
    schemas.extend(_getZenPackSchemas())
    return Schema(*schemas)

ZENOSS_QUEUE_SCHEMA = _loadZenossQueueSchemas()

def _loadAmqpConnectionInfo():
    from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
    from zenoss.protocols.amqpconfig import AMQPConfig
    amqpConnectionInfo = AMQPConfig()
    amqpConnectionInfo.update(getGlobalConfiguration())
    return amqpConnectionInfo

CONNECTION_INFO = _loadAmqpConnectionInfo()

def removeZenPackQueuesExchanges(path):
    """
    Attempts to remove all the queues that the zenpack registered

    @type  Path: string
    @param Path: Absolute path to the zenpack (from zenpack.path())
    """
    schema = _loadQjs(path)
    if not schema:
        # no queues to remove
        return

    connectionInfo = getUtility(IAMQPConnectionInfo)
    queueSchema = getUtility(IQueueSchema)
    amqpClient = BlockingPublisher(connectionInfo, queueSchema)
    channel = amqpClient.getChannel()
    queues = schema[0].get('queues', [])
    exchanges = schema[0].get('exchanges', [])
    log = logging.getLogger('zen.ZenMessaging')

    # queues
    for identifier, queue  in queues.iteritems():
        name = queue['name']
        try:
            substitute_replacements(name, None)
        except MissingReplacementException:
            # Ignore these - they can't be automatically deleted
            continue
        try:
            log.info("Removing queue %s", name)
            channel.queue_delete(name)
        except Exception, e:
            # the queue might already be deleted etc, do not fail if we can't
            # remove it
            log.debug(e)
            log.info("Unable to remove queue %s", name)

    # exchanges
    for identifier, exchange in exchanges.iteritems():
        name = exchange['name']
        try:
            log.info("Removing exchange %s", name)
            channel.exchange_delete(name)
        except Exception, e:
            # the queue might already be deleted etc, do not fail if we can't
            # remove it
            log.debug(e)
            log.info("Unable to remove exchange %s", name)
    amqpClient.close()
