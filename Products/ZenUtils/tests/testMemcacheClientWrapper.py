##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import memcache
import types
import unittest
import uuid
import relstorage.storage

from contextlib import contextmanager

from Products.ZenUtils.memcacheClientWrapper import createModule

@contextmanager
def mockMemcacheClient():
    """ Replace memcache.Client class with a mock """
    class MockClient(object):
        instances = []
        def __init__(self, *args, **kwargs):
            self.initArgs = args
            self.initKwargs = kwargs
            MockClient.instances.append(self)
    original = memcache.Client
    memcache.Client = MockClient
    yield MockClient
    memcache.Client = original


class TestMemcacheClientWrapper(unittest.TestCase):
    """ Tests the memcacheClientWrapper module """

    def testModuleImportStatic(self):
        moduleName = 'foo'
        kwargs = {'foo':1, 'bar':2}
        createModule(moduleName, **kwargs)
        try:
            import foo
        except:
            self.fail("Could not import module")
        self.assertTrue(type(foo) is types.ModuleType)

    def testModuleImportDynamic(self):
        moduleName = str(uuid.uuid4())
        kwargs = {'foo':1, 'bar':moduleName}
        createModule(moduleName, **kwargs)
        module = __import__(moduleName, {}, {}, [])
        self.assertTrue(type(module) is types.ModuleType)
        self.assertEqual(module.__name__, moduleName)

    def testModuleContainsClientClass(self):
        moduleName = str(uuid.uuid4())
        kwargs = {'foo':1, 'bar':moduleName}
        createModule(moduleName, **kwargs)
        module = __import__(moduleName, {}, {}, [])
        self.assertTrue('Client' in module.__dict__)
        # module.Client is a class
        self.assertTrue(type(module.Client) is type)

    def testClientOveridesInitializer(self):
        moduleName = str(uuid.uuid4())
        kwargs = {'foo':1, 'bar': moduleName}
        args = (1,2,'woot')
        with mockMemcacheClient():
            createModule(moduleName, **kwargs)
            module = __import__(moduleName, {}, {}, [])
            client = module.Client(*args)
        self.assertEqual(client.initArgs, args)
        self.assertEqual(client.initKwargs, kwargs)

    def testClientArgOveride(self):
        moduleName = str(uuid.uuid4())
        moduleKwargs = {'foo':1, 'bar': moduleName}
        initializerKwargs = {'foo':11, 'baz':None}
        with mockMemcacheClient():
            createModule(moduleName, **moduleKwargs)
            module = __import__(moduleName, {}, {}, [])
            client = module.Client(**initializerKwargs)
        expected = dict(moduleKwargs, **initializerKwargs)
        self.assertEqual(client.initKwargs, expected)

    def testRelstorageUsesModule(self):
        """ Constructing a RelStorage object uses the given module's Client """
        moduleName = str(uuid.uuid4())
        kwargs = {'foo':1, 'bar': moduleName}
        relstoreParams = {
                'cache_module_name': moduleName,
                'cache_servers': ('localhost:1234',)
                }
        with mockMemcacheClient() as mockClientClass:
            createModule(moduleName, **kwargs)
            relstorage.storage.RelStorage(None, create=False, **relstoreParams)
        self.assertEqual(len(mockClientClass.instances), 1)
        client = mockClientClass.instances[0]
        self.assertEqual(client.initKwargs, kwargs)
