##############################################################################
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

class ServiceTree (object):
    """
    This class allows for the caching and traversal of trees comprised of
    ServiceDefinition objects.
    """

    def __init__(self, services=[]):
        """
        :param services: all services in the tree
        :type services: list of ServiceDefinition objects
        """
        self.setServices(services)


    def setServices(self, services):
        """
        Set the state of the service tree

        :param services: all services in the tree
        :type services list of ServiceDefinition objects
        """
        self._services = services
        self._idToService = dict((i.id, i) for i in services)
        self._serviceChildren = dict((i, []) for i in services)
        for i in (i for i in services if i.parentId):
            self._serviceChildren[self._idToService[i.parentId]].append(i)


    def getChildren(self, service):
        """
        Returns a list of all child services of a given service

        @param service: the service for which to return children
        @type service: service object or string containing service id
        @rtype: list of service objects
        """
        if isinstance(service, basestring):
            service = self._idToService[service]
        return self._serviceChildren[service]


    def getService(self, serviceId):
        """
        Return the service object corresponding to a given service id

        @param serviceId: the service id
        @type serviceId: string
        @rtype: ServiceDefinition object
        """
        return self._idToService[serviceId]


    def matchServicePath(self, currentServiceId, path):
        """
        Return a list of services which match the given service path

        A "service path" is a string which applies file-system semantics to the
        service hierarchy.  I.e., it is a string of components separated by slashes.
        Like a FS path it may be absolute (i.e, beginning with '/') or relative;
        absolute means that it starts with the root of the tree containing the
        given current service.  Legitimate components include '.' and '..' with
        the same semantics as in FS paths.  Components which are identifiers are
        matched against the tags of the candidate services; this implies that a path
        can match multiple services at any given level.

           e.g., '/hub/collector' will match all services tagged 'collector' inside
           all services tagged 'hub' which are children of the root service.

        @param currentServiceId: id of service from which to do relative path matching
        @param currentServiceId: string
        @param path: path to match
        @param path: string
        @rtype: list of ServiceDefinition objects
        """
        service = self._idToService[currentServiceId]
        if path.startswith('/'):
            # absolute path; find the root of the current service tree
            path = path[1:]
            while service.parentId:
                 service = self.getService(service.parentId)
        current = [service]

        for component in path.split('/'):
            if component in ('.', ''):
                pass
            elif component == '..':
                current = [self._idToService[i.parentId] if i.parentId else i
                            for i in current]
            else:
                next = []
                for service in current:
                    children = self._serviceChildren[service]
                    next.extend (i for i in children if component in i.tags)
                current = next
        return current


