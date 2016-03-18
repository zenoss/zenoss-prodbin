#!/usr/bin/env python

import importlib
import difflib
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
            for datum in json.loads(open(jsonfile, 'r').read()):
                self.services.append(service.deserialize(datum))
            self.version = self.services[0]._Service__data["Version"]

        def commit(self, filename=None):
            addedServices = []
            modifiedServices = []
            for svc in self.services:
                if not hasattr(svc, '_Service__data'):
                    svc._Service__data = {}
                serial = service.serialize(svc)
                serial["ID"] = serial.get('ID', 'new-service')
                serial["Version"] = self.version
                if serial["ID"] == "new-service":
                    addedServices.append(serial)
                else:
                    modifiedServices.append(serial)

        def deployService(self, servicedef, parent):
            if parent._Service__data['ID'] == 'new-service':
                raise Exception("Can't deploy a service to a parent that is a new service.")
            newservice = service.deserialize(json.loads(servicedef))
            newservice._Service__data["ParentServiceID"] = parent._Service__data["ID"]
            self.services.append(newservice)

        def servicedef(self):
            """
            This method is not available to the real ServiceContext.
            It's only here for testing purposes.
            """
            return sorted([service.serialize(s) for s in self.services], key=lambda s: s['Name'])

    return FakeServiceContext()

class FakeDmd:

    def __init__(self):
        None

    def getProductName(self):
        return "Resource Manager"


def compare(this, that, path=None):
    path = path or []
    iab = []
    if isinstance(this, list):
        if not isinstance(that, list):
            return False, path, None
        if len(this) != len(that):
            return False, path, None
        iab = enumerate(zip(this, that))
    elif isinstance(this, dict):
        if not isinstance(that, dict):
            return False, path, None
        if len(this.keys()) != len(that.keys()):
            for key in list(set(this.keys() + that.keys())):
                if this.get(key) != this.get(key):
                    return False, path + [key], None
        keys = this.keys()
        iab = zip(keys, [(this.get(k), that.get(k)) for k in keys])
    elif isinstance(this, basestring):
        if this == that:
            return True, None, None
        dis = this.split('\n')
        dat = that.split('\n')
        return False, path, difflib.unified_diff(dis, dat)
    else:
        if this != that:
            return False, path, None
    for i, (a, b) in iab:
        r, p, n = compare(a, b, path + [i])
        if not r:
            return False, p, n
    return True, None, None


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
        if hasattr(self, 'dmd'):
            dmd = self.dmd
        else:
            dmd = FakeDmd()
        with mock.patch(sm_context, new=lambda: context):
            with mock.patch.dict('os.environ', {'SERVICED_SERVICE_IMAGE': '67nh3y829fh3dsemstmfjpg11/resmgr_5.0:latest'}):
                getattr(migration, self.migration_class_name)().cutover(dmd)
        actual = context.servicedef()
        expected = fakeContextFromFile(svcdef_after).servicedef()
        result, rpath, rdiff = compare(actual, expected)
        if not result:
            e, a = expected, actual
            for p in rpath:
                e, a = e[p], a[p]
            e = ('None' if e is None else e) or '""'
            a = ('None' if a is None else a) or '""'
            fpath = '.'.join([str(p) for p in rpath])
            if rdiff is not None:
                self.fail("Migration failed: Unified Diff at %s:\n\n%s\n"
                        % (rpath, "\n".join(rdiff)))
            else:            
                self.fail("Migration failed: Expected\n\n%s\n\n at %s, got \n\n%s\n\n instead."
                        % (e, rpath, a))


    def test_cutover_correctness(self):
        self._test_cutover(self.initial_servicedef, self.expected_servicedef)

    def test_cutover_idempotence(self):
        self._test_cutover(self.expected_servicedef, self.expected_servicedef)
