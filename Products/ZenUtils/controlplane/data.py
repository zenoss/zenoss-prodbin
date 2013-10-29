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

    'get' result example
    {
        "Id":              "zentrap",
        "Name":            "Trapful",
        "Startup":         "/bin/true",
        "Description":     "This is a collector deamon 4",
        "Instances":       0,
        "ImageId":         "zenoss",
        "PoolId":          "default",
        "DesiredState":    1,
        "Launch":          "auto",
        "Endpoints":       null,
        "ParentServiceId": "localhost",
        "CreatedAt":       "0001-01-01T00:00:00Z",
        "UpdatedAt":       "2013-10-29T07:31:22-05:00"
    }
    missing current-state, pid, conf, and log.
    
    {
        "id":     <string>,
        "name":   <string>,
        "uri":    <string>,
        "tags":   [<string>, ...],
        "log":    <uri-string>,
        "conf":   <uri-string>,
        "status": <string>,
        "state":  <string>,
        "pid":    <integer>,
    }
"""


def json2ServiceApplication(obj):
    try:
        args = {
            "url":              obj.get("uri"),
            "id":               obj.get("Id"),
            "name":             obj.get("Name"),
            "description":      obj.get("Description"),
            "logResourceId":    obj.get("log"),
            "configResourceId": obj.get("conf"),
            "status":           obj.get("Launch") == "auto",
            "currentState":     obj.get("CurrentState"),
            "desiredState":     obj.get("DesiredState"),
            "pid":              obj.get("pid")
        }
        return ServiceApplication(**args)
    except KeyError as ex:
        raise ValueError("Invalid JSON document; %s: %s" % (ex, obj))


class ServiceApplication(object):
    """
    """

    STATES = type('enum_states', (object,), dict(
        (name, value) for value, name in enumerate(
            ("STARTED", "RUNNING", "STOPPED", "UNKNOWN")
        )
    ))()

    def __init__(self, **kwargs):
        """
        """
        self._id = kwargs.get("id")
        self._url = kwargs.get("url")
        self._pid = kwargs.get("pid")
        self._name = kwargs.get("name")
        self._description = kwargs.get("description")
        self._status = kwargs.get("status")
        self._currentstate = kwargs.get("currentState", "UNKNOWN")
        self._desiredstate = kwargs.get("desiredState")
        self._logurl = kwargs.get("logResourceId")
        self._confurl = kwargs.get("configResourceId")

    @property
    def id(self):
        return self._id
    
    @property
    def resourceId(self):
        return self._url

    @property
    def processId(self):
        return self._pid

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = bool(value)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value not in self.STATES:
            raise ValueError("Invalid state: %s", value)
        self._state = value

    @property
    def logResourceId(self):
        return self._logurl

    @property
    def configResourceId(self):
        return self._configurl


# Define the names to export via 'from data import *'.
__all__ = (
    "json2ServiceApplication", "ServiceApplication"
)
