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
import fnmatch
import json
import logging
import urllib
import urllib2

from cookielib import CookieJar
from urlparse import urlunparse

from .data import (ServiceJsonDecoder, ServiceJsonEncoder, HostJsonDecoder,
                   ServiceStatusJsonDecoder)


_DEFAULT_PORT = 443
_DEFAULT_HOST = "localhost"


LOG = logging.getLogger("zen.controlplane.client")


class ControlCenterError(Exception): pass


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


class ControlPlaneClient(object):
    """
    """

    def __init__(self, user, password, host=None, port=None):
        """
        """
        self._cj = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self._cj)
        )
        self._server = {
            "host": host if host else _DEFAULT_HOST,
            "port": port if port else _DEFAULT_PORT,
        }
        self._creds = {"username": user, "password": password}
        self._netloc = "%(host)s:%(port)s" % self._server

    def queryServices(self, name=None, tags=None, tenantID=None):
        """
        Returns a sequence of ServiceDefinition objects that match
        the given requirements.
        """
        query = {}
        if name:
            namepat = fnmatch.translate(name)
            # controlplane regex accepts \z, not \Z.
            namepat = namepat.replace("\\Z", "\\z")
            query["name"] = namepat
        if tags:
            if isinstance(tags, (str, unicode)):
                tags = [tags]
            query["tags"] = ','.join(tags)
        if tenantID:
            query["tenantID"] = tenantID
        response = self._dorequest("/services", query=query)
        body = ''.join(response.readlines())
        response.close()
        decoded = ServiceJsonDecoder().decode(body)
        if decoded is None:
            decoded = []
        return decoded

    def getService(self, serviceId, default=None):
        """
        Returns the ServiceDefinition object for the given service.
        """
        response = self._dorequest("/services/%s" % serviceId)
        body = ''.join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def updateService(self, service):
        """
        Updates the definition/state of a service.

        :param ServiceDefinition service: The modified definition
        """
        body = ServiceJsonEncoder().encode(service)
        LOG.info("Updating service '%s':%s", service.name, service.id)
        LOG.debug("Updating service %s", body)
        response = self._dorequest(
            service.resourceId, method="PUT", data=body
        )
        body = ''.join(response.readlines())
        response.close()

    def startService(self, serviceId):
        """
        Start the given service

        :param string ServiceId: The service to start
        """
        LOG.info("Starting service '%s", serviceId)
        response = self._dorequest("/services/%s/startService" % serviceId,
                                   method='PUT')
        body = ''.join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def stopService(self, serviceId):
        """
        Stop the given service

        :param string ServiceId: The service to stop
        """
        LOG.info("Stopping service '%s", serviceId)
        response = self._dorequest("/services/%s/stopService" % serviceId,
                                   method='PUT')
        body = ''.join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def addService(self, serviceDefinition):
        """
        Add a new service

        :param string serviceDefinition: json encoded representation of service
        :returns string: json encoded representation of new service's links
        """
        LOG.info("Adding service")
        LOG.debug(serviceDefinition)
        response = self._dorequest(
            "/services/add", method="POST", data=serviceDefinition
        )
        body = ''.join(response.readlines())
        response.close()
        return body

    def deleteService(self, serviceId):
        """
        Delete a service

        :param string serviceId: Id of the service to delete
        """
        LOG.info("Removing service %s", serviceId)
        response = self._dorequest(
            "/services/%s" % serviceId, method="DELETE"
        )
        response.close()

    def deployService(self, parentId, service):
        """
        Deploy a new service

        :param string parentId: parent service id
        :param string service: json encoded representation of service
        :returns string: json encoded representation of new service's links
        """
        LOG.info("Deploying service")
        data = {
            'ParentID': parentId,
            'Service': json.loads(service)
        }
        LOG.debug(data)
        response = self._dorequest(
            "/services/deploy", method="POST", data=json.dumps(data)
        )
        body = ''.join(response.readlines())
        response.close()
        return body

    def queryServiceInstances(self, serviceId):
        """
        Returns a sequence of ServiceInstance objects.
        """
        response = self._dorequest("/services/%s/running" % serviceId)
        body = ''.join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)


    def queryServiceStatus(self, serviceId):
        """
        Returns a sequence of ServiceInstance objects.
        """
        response = self._dorequest("/services/%s/status" % serviceId)
        body = ''.join(response.readlines())
        response.close()
        return ServiceStatusJsonDecoder().decode(body)

    def queryHosts(self):
        """
        Returns a sequence of Host objects.
        """
        response = self._dorequest("/hosts")
        body = ''.join(response.readlines())
        response.close()
        return HostJsonDecoder().decode(body)

    def getHost(self, hostId):
        """
        Returns a sequence of Host objects.
        """
        response = self._dorequest("/hosts/%" % hostId)
        body = ''.join(response.readlines())
        response.close()
        return HostJsonDecoder().decode(body)

    def getInstance(self, serviceId, instanceId, default=None):
        """
        Returns the requested ServiceInstance object.
        """
        response = self._dorequest(
            "/services/%s/running/%s" % (serviceId, instanceId)
        )
        body = ''.join(response.readlines())
        response.close()
        return ServiceJsonDecoder().decode(body)

    def getServiceLog(self, serviceId, start=0, end=None):
        """
        """
        response = self._dorequest("/services/%s/logs" % serviceId)
        body = ''.join(response.readlines())
        response.close()
        log = json.loads(body)
        return log["Detail"]

    def getInstanceLog(self, serviceId, instanceId, start=0, end=None):
        """
        """
        response = self._dorequest(
            "/services/%s/%s/logs" % (serviceId, instanceId)
        )
        body = ''.join(response.readlines())
        response.close()
        log = json.loads(body)
        return str(log["Detail"])

    def killInstance(self, hostId, instanceId):
        """
        """
        response = self._dorequest(
            "/hosts/%s/%s" % (hostId, instanceId), method="DELETE"
        )
        response.close()

    def _makeRequest(self, uri, method=None, data=None, query=None):
        query = urllib.urlencode(query) if query else ""
        url = urlunparse(("https", self._netloc, uri, "", query, ""))
        args = {}
        if method:
            args["method"] = method
        if data:
            args["data"] = data
            args["headers"] = {"Content-Type": "application/json"}
        return _Request(url, **args)

    def _login(self):
        # Clear the cookie jar before logging in.
        self._cj.clear()
        encodedbody = json.dumps(self._creds)
        request = self._makeRequest("/login", data=encodedbody)
        response = self._opener.open(request)
        response.close()
        self._opener.close()

    def _dorequest(self, uri, method=None, data=None, query=None):
        # Try to perform the request up to five times
        for trycount in range(5):
            request = self._makeRequest(uri, method=method, data=data, query=query)
            try:
                return self._opener.open(request)
            except urllib2.HTTPError as ex:
                if ex.getcode() == 401:
                    self._login()
                    continue
                elif ex.getcode() == 500:
                    # Make the exception prettier and reraise it
                    try:
                        msg = json.load(ex)
                    except ValueError:
                        raise ex  # This stinks because we lose the stack
                    detail = msg.get('Detail')
                    if not detail:
                        raise
                    detail = detail.replace("Internal Server Error: ", "")
                    raise ControlCenterError(detail)
                raise
            else:
                # break the loop so we skip the loop's else clause
                break
        else:
            # raises the last exception that was raised (the 401 error)
            raise


# Define the names to export via 'from client import *'.
__all__ = (
    "ControlPlaneClient",
)
