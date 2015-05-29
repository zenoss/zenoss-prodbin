# #
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#
import functools
import os
import json
import cStringIO

from contextlib import contextmanager

import Globals
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.ZenPack import ZenPack, DirectoryConfigContents
import Products.ZenModel.ZenPack
import servicemigration
import __builtin__

class _MockControlPlaneClient(object):
    def __call__(self, *args, **kwargs):
        return self
    def __init__(self, services=[], **kwargs):
        self._services = services
        self._added, self._deleted = [], []
    def queryServices(self, query):
        return self._services
    def deployService(self, parent, service):
        self._added.append((parent, service))
        svcDict = json.loads(service)
        self._services.append(_MockService(svcDict['Id'], parent, svcDict['Tags']))
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
        self._data = {}
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

class _MockServiceMigrationContext(object):
    def __call__(self, *args, **kwargs):
        return self
    def __init__(self):
        self._added = []
    def _ServiceContext__deployService(self, service, parentid):
        self._added.append((parentid, service))
    def commit(self):
        return
    @property
    def added(self):
        return self._added

@contextmanager
def setServiceMigrationContext(context):
    try: 
        save = servicemigration.ServiceContext
        servicemigration.ServiceContext = context
        yield
    finally:
        servicemigration.ServiceContext = save


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


def createMockLoadServiceDefinitions(fileDict):
    def dummyServiceDefinitions(name):
        return json.dumps(fileDict[name])
    return dummyServiceDefinitions

@contextmanager
def setBuiltinOpen(fileDict):
    try:
        builtin_open = __builtin__.open
        def _open(name, mode='r'):
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
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        service = {
            "servicePath": "/hub",
            "serviceDefinition": _MockService('id','pid').toJsonDict()
        }
        with setControlPlaneClient(client), setServiceMigrationContext(context):
            ZenPack("id").installServices([service])
        self.assertEquals(context.added, [])

    def testAddSingleService(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        service = _MockService('id','pid')
        service.poolId = 'not_default'
        service = {
            "servicePath": "/hub",
            "serviceDefinition": service.toJsonDict()
        }
        #json.dumps(service, cls=_MockServiceEncoder)
        with setControlPlaneClient(client), setServiceMigrationContext(context), setCurrentService('zope'):
            ZenPack("id").installServices([service])
        self.assertEquals(len(context.added), 1)
        parent, added = context.added[0][0], json.loads(context.added[0][1])
        self.assertEquals(added['Id'], 'id')
        self.assertEquals(parent, 'hub1')

    def testAddMultipleServices(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        services = [{
            "servicePath": "/",
            "serviceDefinition": _MockService("id1").toJsonDict()
        }, {
            "servicePath": "/hub",
            "serviceDefinition": _MockService("id2").toJsonDict()
        }]
        # services = [json.dumps(_MockService(i), cls=_MockServiceEncoder)
        #             for i in ('id1', 'id2')]
        # paths = ['/', '/hub']
        with setControlPlaneClient(client), setServiceMigrationContext(context), setCurrentService('zope'):
            ZenPack("id").installServices(services)
        self.assertEquals(len(context.added), 2)
        added = [(i[0], json.loads(i[1])) for i in context.added]
        self.assertEquals(added[0][1]['Id'], 'id1')
        self.assertEquals(added[0][0], 'zenoss')
        self.assertEquals(added[1][1]['Id'], 'id2')
        self.assertEquals(added[1][0], 'hub1')

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

    def testNormalizeServiceLogConfigs(self):
        sampleLogConfig = {
            'filters': ['supervisord'], 'path': '/opt/zenoss/log/Z2.log', 'type': 'pythondaemon'}
        auditLogConfig = {
            'filters': ['supervisord'], 'path': '/opt/zenoss/log/audit.log', 'type': 'zenossaudit'}
        tests = (
                {},
                {'LogConfigs':[]},
                {'LogConfigs':[auditLogConfig]},
                {'LogConfigs':[sampleLogConfig]},
                {'LogConfigs':[sampleLogConfig, auditLogConfig]},
                {'LogConfigs':[auditLogConfig, sampleLogConfig]}
        )
        for service in tests:
            inputLength = len(service.get('LogConfigs', []))
            if auditLogConfig in service.get('LogConfigs', []):
                ZenPack.normalizeService(service, '')
                LogConfigs = service['LogConfigs']
                self.assertEquals(len(LogConfigs), inputLength)
            else:
                ZenPack.normalizeService(service, '')
                LogConfigs = service['LogConfigs']
                self.assertEquals(len(LogConfigs), inputLength+1)
            self.assertIn(auditLogConfig, LogConfigs)

    def testNormalizeServiceTags(self):
        tag = 'foobar'
        tests = ({},{"Tags": ['some', 'tags']})
        for service in tests:
            ZenPack.normalizeService(service, tag)
            self.assertIn(tag, service["Tags"])

    def testNormalizeServiceImage(self):
        try:
            image = 'foobar'
            os.environ['SERVICED_SERVICE_IMAGE'] = image
            tests = (({'ImageID':''}, image),
                     ({'ImageID':'xxx'}, 'xxx'))
            for service, expected in tests:
                ZenPack.normalizeService(service, '')
                self.assertEquals(service["ImageID"], expected)
        finally:
            del os.environ['SERVICED_SERVICE_IMAGE']

    def testDirectoryConfigContents(self):
        fileDict = {'/foo/bar/baz/qux': 'barge'}
        with setBuiltinOpen(fileDict):
            dcc = DirectoryConfigContents('/foo/bar')
            self.assertEquals(dcc['/baz/qux'], '"barge"')
            with self.assertRaises(KeyError): dcc['no_such_file']
            with self.assertRaises(KeyError): dcc[1]


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenpackServices))
    return suite
