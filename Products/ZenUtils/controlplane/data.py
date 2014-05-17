##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Application JSON format:

    'query' result
    [
        <application-node>,...
    ]

    /services/<service-id> 'get' result example
    {
        "Id":              "9827-939070095",
        "Name":            "zentrap",
        "Startup":         "/bin/true",
        "Description":     "This is a collector deamon 4",
        "Instances":       0,
        #"Running": [
        #    {
        #      "Id": "28ea1c28-8491-2afc-fd9d-fe207046be05",
        #      "ServiceID": "c412e4cf-48be-b53d-d144-867ffa596ffa",
        #      "HostId": "007f0101",
        #      "DockerID": "3b52fc18767f",
        #      "StartedAt": "2013-10-29T17:59:13-05:00",
        #    }
        #]
        "ConfigFiles": {
            "/etc/my.cnf": {
                "Filename": "/etc/my.cnf",
                "Owner": "",
                "Permissions": 0,
                "Content": "\n# SAMPLE config file for mysql\n\n[mysqld]\n\ninnodb_buffer_pool_size = 16G\n\n"
            }
        },
        "ImageID":         "zenoss",
        "PoolId":          "default",
        "DesiredState":    1,
        "Launch":          "auto",
        "Endpoints":       {
            "Protocol" : "tcp",
            "PortNumber": 6379,
            "Application": "redis",
            "Purpose": "export"
        },
        "ParentServiceID": "293482085035",
        "CreatedAt":       "0001-01-01T00:00:00Z",
        "UpdatedAt":       "2013-10-29T07:31:22-05:00"
    }
    missing current-state, conf, and log.

    /services/<service-id>/running example
    [
      {
        "Id": "28ea1c28-8491-2afc-fd9d-fe207046be05",
        "ServiceID": "c412e4cf-48be-b53d-d144-867ffa596ffa",
        "HostId": "007f0101",
        "DockerID": "3b52fc18767f",
        "StartedAt": "2013-10-29T17:59:13-05:00",
        "Name": "redis",
        "Startup": "/usr/sbin/redis-server",
        "Description": "",
        "Instances": 1,
        "ImageID": "zenoss/redis",
        "PoolId": "default",
        "DesiredState": 1,
        "ParentServiceID": ""
      }
    ]

    {
        "id":     <string>,
        "name":   <string>,
        "uri":    <string>,
        "tags":   [<string>, ...],
        "log":    <uri-string>,
        "conf":   <uri-string>,
        "status": <string>,
        "state":  <string>,
    }
"""

import json
from datetime import datetime
from functools import wraps

from zope.component import createObject
from zope.component.factory import Factory
from zope.interface import implementer

from .interfaces import IServiceDefinition, IServiceInstance


class _Value(object):
    """
    Helper class for creating objects that can behave as named
    constants that (optionally) convertable to an integer.
    """

    def __init__(self, name, value=None):
        self._name = name
        self._value = value if value is not None else name

    def __str__(self):
        return self._name

    def __int__(self):
        return int(self._value)

    def __repr__(self):
        return str(self._value)


# The set of keys found in a service definition JSON object.
# Used to identify such objects.
_definitionKeys = set([
    "Id", "Name", "ParentServiceID", "PoolId", "Description", "Launch",
    "DesiredState", "Tags", "ConfigFiles"
])

# The set of keys found in a service instance JSON object.
# Used to identify such objects.
_instanceKeys = set([
    "Id", "ServiceID", "HostId", "DockerID", "StartedAt", "Name",
    "Startup", "Description", "Instances", "ImageID",
    "PoolId", "DesiredState", "ParentServiceID"
])


def _decodeServiceJsonObject(obj):
    foundKeys = _definitionKeys & set(obj.keys())
    if foundKeys == _definitionKeys:
        service = createObject("ServiceDefinition")
        service.__setstate__(obj)
        return service
    foundKeys = _instanceKeys & set(obj.keys())
    if foundKeys == _instanceKeys:
        instance = createObject("ServiceInstance")
        instance.__setstate__(obj)
        return instance
    return obj


class ServiceJsonDecoder(json.JSONDecoder):
    """
    """

    def __init__(self, **kwargs):
        kwargs.update({"object_hook": _decodeServiceJsonObject})
        super(ServiceJsonDecoder, self).__init__(**kwargs)


class ServiceJsonEncoder(json.JSONEncoder):
    """
    """

    def default(self, o):
        if isinstance(o, ServiceDefinition):
            return o.__getstate__()
        return JSONEncoder.default(self, o)

def _convertToDateTime(f):
    @wraps(f)
    def wrapper(*args, **kw):
        src = f(*args, **kw)
        trimmed = src[:19]
        if len(trimmed) == 19:
            return datetime.strptime(trimmed, "%Y-%m-%dT%H:%M:%S")
    return wrapper


@implementer(IServiceInstance)
class ServiceInstance(object):
    """
    """

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    def __init__(self):
        self._data = {}

    @property
    def id(self):
        return self._data.get("Id")

    @property
    def resourceId(self):
        return "/services/%s/running/%s" % (
            self._data.get("ServiceID"), self._data.get("Id")
        )

    @property
    def serviceId(self):
        return self._data.get("ServiceID")

    @property
    def hostId(self):
        return self._data.get("HostId")

    @property
    @_convertToDateTime
    def startedAt(self):
        return self._data.get("StartedAt")


class ServiceInstanceFactory(Factory):
    """
    Factory for ServiceInstance objects.
    """

    def __init__(self):
        super(ServiceInstanceFactory, self).__init__(
            ServiceInstance, "ServiceInstance",
            "Control Plane Service Instance Description"
        )


@implementer(IServiceDefinition)
class ServiceDefinition(object):
    """
    """

    class LAUNCH_MODE(object):
        AUTO = _Value("AUTO", "auto")
        MANUAL = _Value("MANUAL", "manual")

    class STATE(object):
        RUN = _Value("RUN", 1)
        STOP = _Value("STOP", 0)
        RESTART = _Value("RESTART", -1)

    __map = {
        1: STATE.RUN, 0: STATE.STOP, -1: STATE.RESTART
    }

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    def __init__(self):
        """
        """
        self._data = {}

    @property
    def id(self):
        return self._data.get("Id")

    @property
    def parentId(self):
        return self._data.get('ParentServiceID')

    @property
    def poolId(self):
        return self._data.get('PoolId')

    @property
    def resourceId(self):
        return "/services/%s" % (self._data.get("Id"),)

    @property
    def name(self):
        return self._data.get("Name")

    @property
    def description(self):
        return self._data.get("Description")

    @property
    def tags(self):
        return self._data.get("Tags")

    @property
    def launch(self):
        return self.LAUNCH_MODE.__dict__.get(self._data.get("Launch").upper())

    @launch.setter
    def launch(self, value):
        if str(value) not in self.LAUNCH_MODE.__dict__:
            raise ValueError("Invalid status value: %s" % (value,))
        self._data["Launch"] = repr(value)

    @property
    def desiredState(self):
        return self.__map.get(self._data.get("DesiredState"))

    @desiredState.setter
    def desiredState(self, value):
        if str(value) not in self.STATE.__dict__:
            raise ValueError("Invalid state: %s" % (value,))
        self._data["DesiredState"] = int(value)

    @property
    def logResourceId(self):
        return self._data.get("LogId")

    @property
    def configFiles(self):
        """
        Returns a dict with this format:

           {
               "<filename>": {
                  "FileName": "<filename>",
                  "Content": "<contents-of-file-as-string>"
               },
               ...
           }

        The top-level keys are duplicated by the "FileName" key in the
        children dictionaries.
        """
        return self._data.get("ConfigFiles", {})

    @property
    @_convertToDateTime
    def createdAt(self):
        return self._data.get("CreatedAt")

    @property
    @_convertToDateTime
    def updatedAt(self):
        return self._data.get("UpdatedAt")


class ServiceDefinitionFactory(Factory):
    """
    Factory for ServiceDefinition objects.
    """

    def __init__(self):
        super(ServiceDefinitionFactory, self).__init__(
            ServiceDefinition, "ServiceDefinition",
            "Control Plane Service Definition"
        )


# Define the names to export via 'from data import *'.
__all__ = (
    "ServiceJsonDecoder", "ServiceJsonEncoder",
    "ServiceDefinition", "ServiceDefinitionFactory",
    "ServiceInstance", "ServiceInstanceFactory"
)
