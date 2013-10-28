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

    'get' result
    {
        "uri":    <string>,
        "id":     <string>,
        "name":   <string>,
        "tags":   [<string>, ...],
        "log":    <uri-string>,
        "conf":   <uri-string>,
        "status": <string>,
        "state":  <string>,
        "pid":    <integer>,
    }
"""

_app1 = """{"uri": "uri-to-app", "id": "app-uuid", "name": "app-name", "tags": ["daemon"], "log": "uri-to-app-log", "conf": "uri-to-app-conf", "status": "ENABLED", "state": "RUNNING", "pid": 5}"""

_app2 = """{"uri": "uri-to-app2", "id": "app2-uuid", "name": "app2-name", "tags": ["daemon"], "log": "uri-to-app2-log", "conf": "uri-to-app2-conf", "status": "DISABLED", "state": "STOPPED", "pid": null}"""

_apps = "[%s,%s]" % (_app1, _app2)


def json2ServiceApplication(obj):
    try:
        args = {
            "url": obj["uri"],
            "id": obj["id"],
            "name": obj["name"],
            "logResourceId": obj["log"],
            "configResourceId": obj["conf"],
            "status": obj["status"],
            "state": obj["state"],
            "pid": obj.get("pid")
        }
        return ServiceApplication(**args)
    except KeyError as ex:
        raise ValueError("Invalid JSON document; %s: %s" % (ex, obj))


class ServiceApplication(object):
    """
    """

    STATES = type('enum_states', (object,), dict(
        (name, value) for value, name in enumerate(
            ("STARTING", "STARTED", "RUNNING", "STOPPING", "STOPPED")
        )
    ))()

    def __init__(self, **kwargs):
        """
        """
        self._id = kwargs["id"]
        self._url = kwargs["url"]
        self._pid = kwargs.get("pid")
        self._name = kwargs["name"]
        self._description = ""
        self._status = kwargs["status"]
        self._state = kwargs["state"]
        self._logurl = kwargs["logResourceId"]
        self._confurl = kwargs["configResourceId"]

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
