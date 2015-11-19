#!/usr/bin/env python

import importlib
import json
import mock
import os

import Globals
from servicemigration import context, service


def fakeContextFromFile(jsonfile):
    jsonfile = os.path.join(os.path.dirname(__file__), jsonfile)
    class FakeServiceContext(context.ServiceContext):

        def __init__(self, filename=None):
            self.services = []
            self.changes = {}
            for datum in json.loads(open(jsonfile, 'r').read()):
                self.services.append(service.deserialize(datum))
            self.version = self.services[0]._Service__data["Version"]

        def commit(self, filename=None):
            addedServices = []
            modifiedServices = []
            for svc in self.services:
                serial = service.serialize(svc)
                serial["Version"] = self.version
                if serial["ID"] == "new-service":
                    addedServices.append(serial)
                else:
                    modifiedServices.append(serial)
            self.changes = {
                "ServiceID": "FakeServiceContext",
                "Modified": modifiedServices,
                "Added": addedServices,
                "Deploy": None,
            }

        def servicedef(self):
            return [service.serialize(s) for s in self.services]
                    
    return FakeServiceContext()


def compare(this, that, path=None):
    path = path or []
    iab = []
    if isinstance(this, list):
        if len(this) != len(that):
            return False, path
        iab = enumerate(zip(this, that))
    elif isinstance(this, dict):
        if len(this.keys()) != len(that.keys()):
            return False, path
        keys = this.keys()
        iab = zip(keys, [(this.get(k), that.get(k)) for k in keys])
    else:
        if this != that:
            return False, path
    for i, (a, b) in iab:
        r, p = compare(a, b, path + [i])
        if not r:
            return False, p
    return True, None


class ServiceMigrationTestCase(object):
    """
    Superclass of service migration tests.
    Supply the migration module and class, the input servicedef file,
    and the output servicedef file.
    """
    initial_servicedef = ''
    expected_servicedef = ''
    migration_module_name = ''
    migration_class_name = ''

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _test_cutover(self, svcdef_before, svcdef_after):
        context = fakeContextFromFile(svcdef_before)
        module_name = 'Products.ZenModel.migrate.%s' % self.migration_module_name
        sm_context = '%s.sm.ServiceContext' % module_name
        migration = importlib.import_module(module_name)
        with mock.patch(sm_context, new=lambda: context):
            step = getattr(migration, self.migration_class_name)().cutover(None)
        actual = context.servicedef()
        expected = fakeContextFromFile(svcdef_after).servicedef()
        result, rpath = compare(actual, expected)
        if not result:
            e, a = expected, actual
            for p in rpath:
                e, a = e[p], a[p]
            fpath = '.'.join([str(p) for p in rpath])
            self.fail("Migration failed: Expected %s at %s, got %s instead."
                      % (e, rpath, a))


    def test_cutover_correctness(self):
        self._test_cutover(self.initial_servicedef, self.expected_servicedef)

    def test_cutover_idempotence(self):
        self._test_cutover(self.expected_servicedef, self.expected_servicedef)
