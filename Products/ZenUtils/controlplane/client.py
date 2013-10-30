##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
ControlPlaneClient
"""

import json
import urllib
import urllib2

from cookielib import CookieJar
from fnmatch import fnmatch
from urlparse import urlunparse

from zope.interface import implementer

from Products.ZenUtils.GlobalConfig import globalConfToDict

from .interfaces import IControlPlaneClient
from .data import ServiceJsonDecoder, ServiceJsonEncoder, ServiceApplication

_DEFAULT_PORT = 8787
_DEFAULT_HOST = "localhost"


class _Request(urllib2.Request):
    """
    Extend urllib2.Request to override the get_method() method so that
    the HTTP method can be specified.
    """

    def __init__(self, *args, **kwargs):
        self.__method = kwargs.pop("method", None)
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self.__method \
                if self.__method else urllib2.Request.get_method(self)


def _getDefaults(options=None):
    if options is None:
        o = globalConfToDict()
    else:
        o = options
    settings = {
        "host": o.get("controlplane-host", _DEFAULT_HOST),
        "port": o.get("controlplane-port", _DEFAULT_PORT),
        "user": o.get("controlplane-user", "zenoss"),
        "password": o.get("controlplane-password", "zenoss"),
    }
    return settings


@implementer(IControlPlaneClient)
class ControlPlaneClient(object):
    """
    """

    def __init__(self):
        """
        """
        self._cj = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self._cj)
        )
        self._settings = _getDefaults()
        self._netloc = "%(host)s:%(port)s" % self._settings

    def queryServices(self, name="*", **kwargs):
        """
        """
        query = {"Name": name}
        response = self._dorequest("/services", query=query)
        body = ''.join(response.readlines())
        response.close()
        decoded = ServiceJsonDecoder().decode(body)
        return [app for app in decoded if fnmatch(app.name, name)]

    def getService(self, instanceId):
        """
        """
        response = self._dorequest("/services/%s" % instanceId)
        body = ''.join(response.readlines())
        response.close()
        decoded = ServiceJsonDecoder().decode(body)
        return decoded

    def updateService(self, instance):
        """
        """
        body = ServiceJsonEncoder().encode(instance)
        response = self._dorequest(
            instance.resourceId, method="PUT", data=body
        )
        body = ''.join(response.readlines())
        response.close()
        print response.code
        import json
        print json.loads(body)

    def getServiceLog(self, uri, start=0, end=None):
        """
        """

    def getServiceConfiguration(self, uri):
        """
        """

    def updateServiceConfiguration(self, uri, config):
        """
        """

    def _makeRequest(self, uri, method=None, data=None, query=None):
        query = urllib.urlencode(query) if query else ""
        url = urlunparse(("http", self._netloc, uri, "", query, ""))
        args = {}
        if method:
            args["method"] = method
        if data:
            args["data"] = data
            args["headers"] = {"Content-Type": "application/json"}
        return _Request(url, **args)

    def _login(self):
        body = {
            "username": self._settings["user"],
            "password": self._settings["password"]
        }
        encodedbody = json.dumps(body)
        request = self._makeRequest("/login", data=encodedbody)
        response = self._opener.open(request)
        response.close()

    def _dorequest(self, uri, method=None, data=None, query=None):
        request = self._makeRequest(
            uri, method=method, data=data, query=query)
        response = None
        try:
            response = self._opener.open(request)
        except urllib2.HTTPError as ex:
            if ex.getcode() == 401:
                self._login()
                response = self._opener.open(request)
            else:
                raise
        return response


# Define the names to export via 'from client import *'.
__all__ = (
    "ControlPlaneClient",
)
