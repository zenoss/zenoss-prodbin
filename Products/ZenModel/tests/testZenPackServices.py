# #
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
# 
import functools
import json
import cStringIO

from contextlib import contextmanager

import Globals
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.ZenPack import ZenPack
import Products.ZenModel.ZenPack
import __builtin__

class _MockControlPlaneClient(object):
    def __call__(self, *args, **kwargs):
        return self
    def __init__(self, services=[], **kwargs):
        self._services = services
        self._added, self._deleted = [], []
    def queryServices(self, query):
        return self._services
    def addService(self, service):
        self._added.append(service)
    def deleteService(self, serviceId):
        self._deleted.append(serviceId)
    @property
    def added(self):
        return self._added
    @property
    def deleted(self):
        return self._deleted

class _MockService (object):
    def __init__(self, id, parentId = '', tags=[]):
        self.name = id.upper()
        self.id = id
        self.parentId = parentId
        self.tags = tags
        self.poolId= 'default'
    def toJsonDict(self):
        return dict(Id = self.id,
                    ParentId = self.parentId,
                    Tags = self.tags)

class _MockServiceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, _MockService):
            return o.toJsonDict()
        return json.JSONEncoder.default(o)

_services = [
    _MockService('zenoss', '', []),
    _MockService('zope', 'zenoss', ['daemon']),
    _MockService('hub1', 'zenoss', ['hub']),
]

@contextmanager
def setControlPlaneClient(client):
    try:
        save = Products.ZenModel.ZenPack.ControlPlaneClient
        Products.ZenModel.ZenPack.ControlPlaneClient = client
        yield
    finally:
        Products.ZenModel.ZenPack.ControlPlaneClient = save

@contextmanager
def setCurrentService(id):
    try:
        save = ZenPack.currentServiceId
        ZenPack.currentServiceId = id
        yield
    finally:
        ZenPack.currentServiceId = save

@contextmanager
def setBuiltinOpen(fileDict):
    try:
        builtin_open = __builtin__.open
        def _open(name, mode):
            if name in fileDict:
                return cStringIO.StringIO(json.dumps(fileDict[name]))
            else:
                return builtin_open(name, mode)
        __builtin__.open = _open
        yield
    finally:
        __builtin__.open = builtin_open

class TestZenpackServices(ZenModelBaseTest):
    def testAddNoCurrentServiceId(self):
        client = _MockControlPlaneClient(services=_services)
        service = json.dumps(_MockService('id'), cls=_MockServiceEncoder)
        with setControlPlaneClient(client):
            ZenPack("id").installServices(service, "/hub")
        self.assertEquals(client.added, [])

    def testAddSingleService(self):
        client = _MockControlPlaneClient(services=_services)
        service = _MockService('id','pid')
        service.poolId = 'not_default'
        service = json.dumps(service, cls=_MockServiceEncoder)
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").installServices(service, "/hub")
        self.assertEquals(len(client.added), 1)
        added = json.loads(client.added[0])
        self.assertEquals(added['Id'], 'id')
        self.assertEquals(added['ParentServiceId'], 'hub1')
        self.assertEquals(added['PoolId'], 'default')

    def testAddMultipleServices(self):
        client = _MockControlPlaneClient(services=_services)
        services = [json.dumps(_MockService(i), cls=_MockServiceEncoder)
                    for i in ('id1', 'id2')]
        paths = ['/hub', '/']
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").installServices(services, paths)
        self.assertEquals(len(client.added), 2)
        added = [json.loads(i) for i in client.added]
        self.assertEquals(added[0]['Id'], 'id1')
        self.assertEquals(added[0]['ParentServiceId'], 'hub1')
        self.assertEquals(added[1]['Id'], 'id2')
        self.assertEquals(added[1]['ParentServiceId'], 'zenoss')

    def testRemoveNoCurrentServiceId(self):
        moduleName = "Zenpacks.zenoss.Test"
        services = _services + [_MockService('me','hub1',[moduleName])]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client):
            ZenPack("id").removeServices(moduleName)
        self.assertEquals(client.deleted, [])

    def testRemoveServices(self):
        tag =  'MyZenPack'
        services = _services + [
            _MockService('alpha', 'zenoss', [tag]),
            _MockService('beta', 'hub1', [tag]),
        ]
        expected = ['alpha', 'beta']
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").removeServices(tag)
        self.assertEquals(sorted(client.deleted), sorted(expected))

    def testInstallFromFiles(self):
        tag = 'myZenpack'
        E_KEY = 'expectedParentId'  # for this test only - associates path with service
        P_KEY = 'servicePath'       # key defining path at which to install service
        D_KEY = 'serviceDefinition' # key defining service to be installed
        # Mock the filesystem - maps path->json file contents
        fileDict = dict (
            a={P_KEY: '/', D_KEY: {E_KEY:'zenoss'}},
            b={P_KEY: '/hub', D_KEY: {E_KEY:'hub1'}},
            c={P_KEY: '/hub', D_KEY: {E_KEY:'hub1', 'Tags':['whatever']}},
        )
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService('zope'), setBuiltinOpen(fileDict):
            ZenPack('id').installServicesFromFiles(fileDict.keys(), tag)
        self.assertEquals(len(fileDict), len(client.added))
        for i in (json.loads(i) for i in client.added):
            self.assertTrue(tag in i['Tags'])
            self.assertEquals(i['ParentServiceId'], i[E_KEY])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenpackServices))
    return suite

