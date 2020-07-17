##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from Products.ZenHub import XML_RPC_PORT, PB_PORT
from zope.interface import implementer

from .interface import IHubServerConfig


@implementer(IHubServerConfig)
class ModuleObjectConfig(object):
    """API for retrieving server related configuration data."""

    def __init__(self, config):
        self.__config = config

    @property
    def legacy_metric_priority_map(self):
        return self.__config.legacy_metric_priority_map

    @property
    def priorities(self):
        return self.__config.priorities

    @property
    def pools(self):
        return self.__config.pools

    @property
    def executors(self):
        return self.__config.executors

    @property
    def routes(self):
        return self.__config.routes

    @property
    def modeling_pause_timeout(self):
        return self.__config.modeling_pause_timeout

    @property
    def task_max_retries(self):
        return self.__config.task_max_retries

    @property
    def pbport(self):
        return self.__config.pbport

    @property
    def xmlrpcport(self):
        return self.__config.xmlrpcport


##############################################################################
# NOTE
#
# The main.py module is dependent on the contents this module (config.py).
# Specfically, if the 'executors' dict is changed, then main.py
# must also be updated with a corresponding change.
##############################################################################

# Declares the executors where work can be sent.
# "executor-id" : "module-path:class-name"
executors = {
    "event": "Products.ZenHub.server.executors:SendEventExecutor",
    "adm": "Products.ZenHub.server.executors:WorkerPoolExecutor",
    "user": "Products.ZenHub.server.executors:WorkerPoolExecutor",
    "default": "Products.ZenHub.server.executors:WorkerPoolExecutor",
}

# Declares which executor a service call is sent to.
routes = {
    "EventService:sendEvent": "event",
    "EventService:sendEvents": "event",
    "*:applyDataMaps": "adm",
    "*:singleApplyDataMaps": "user",
    "*:*": "default",
}

# Declares worker pools and maps the pool to an executor.
# "pool-id": "executor-id"
pools = {
    "default": "default",
    "adm": "adm",
    "user": "user",
}

priorities = {
    # Declares service call priorities.  The order is from highest priority
    # to lowest priority.  Higher priority service calls are executed much
    # more frequently than lower priority service calls.
    "names": (
        "EVENTS",
        "SINGLE_MODELING",
        "OTHER",
        "CONFIG",
        "MODELING",
    ),

    # Associates service calls with priorities.
    # The ("*:*") mapping must be defined.
    "servicecall_map": {
        "EventService:sendEvent": "EVENTS",
        "EventService:sendEvents": "EVENTS",
        "*:singleApplyDataMaps": "SINGLE_MODELING",
        "*:*": "OTHER",
        "*:getDeviceConfigs": "CONFIG",
        "*:getDeviceConfig": "CONFIG",
        "*:applyDataMaps": "MODELING",
    },

    # Identifies the priority associated with modeling.
    # This is used to pause applyDataMaps processing.
    "modeling": "MODELING",
}


legacy_metric_priority_map = {
    "zenhub.eventWorkList": "EVENTS",
    "zenhub.admWorkList": "MODELING",
    "zenhub.otherWorkList": "OTHER",
    "zenhub.singleADMWorkList": "SINGLE_MODELING",
}

# Limit the number of times ZenHub will retry a task before
# returning it as an error.
task_max_retries = 3


class defaults(object):
    """Default values for options."""

    modeling_pause_timeout = 3600
    xmlrpcport = XML_RPC_PORT
    pbport = PB_PORT


# Maximum number of seconds to pause modeling
# during ZenPack install/upgrade/removal
modeling_pause_timeout = defaults.modeling_pause_timeout

# Port to use for XML-based Remote Procedure Calls (RPC)
xmlrpcport = defaults.xmlrpcport

# Port to use for Twisted's pb service
pbport = defaults.pbport
