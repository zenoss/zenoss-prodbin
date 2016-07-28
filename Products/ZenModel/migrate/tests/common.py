#!/usr/bin/env python

import importlib
import difflib
import json
import mock
import os
from collections import namedtuple

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
            return False, path, compare.Diff(this, that)
        if len(this) != len(that):
            return False, path, compare.Diff(this, that)
        iab = enumerate(zip(this, that))
    elif isinstance(this, dict):
        if not isinstance(that, dict):
            return False, path, compare.Diff(this, that)
        # The json deserialization in serviced matches the fields case-
        #   insensitively, choosing the last match encountered for any field.
        #   The keys are sorted in service-migration, so in the case of 
        #   duplicates the "most lower-case" is the last and therefore wins.
        # Duplicate this behavior when comparing dictionaries.
        this = dict((k.lower(), this[k]) for k in sorted(this.iterkeys()))
        that = dict((k.lower(), that[k]) for k in sorted(that.iterkeys()))
        for key in set(this.iterkeys()) ^ set(that.iterkeys()):
            get_val = lambda d: d.get(key, compare.missingKey) 
            return False, path + [key], compare.Diff(get_val(this), get_val(that))
        iab = [(k, (this.get(k), that.get(k))) for k in this.iterkeys()]
    elif isinstance(this, basestring):
        if this == that:
            return True, None, None
        if not isinstance(that, basestring):
            return False, path, compare.Diff(this, that)
        if any ('\n' in i for i in (this, that)):
            diff = difflib.unified_diff(this.split('\n'), that.split('\n'))
            return False, path, diff
        else:
            return False, path, compare.Diff(this, that)
    else:
        if this != that:
            return False, path, compare.Diff(this, that)
    for i, (a, b) in iab:
        r, p, n = compare(a, b, path + [i])
        if not r:
            return False, p, n
    return True, None, None
compare.Diff = namedtuple('Diff', ['actual', 'expected'])
compare.missingKey = '<<KEY NOT PRESENT>>'


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
            if isinstance(rdiff, compare.Diff):
                self.fail("Migration failed: Expected\n\n%s\n\n at %s, got \n\n%s\n\n instead."
                        % (rdiff.actual, rpath, rdiff.expected))
            else:
                self.fail("Migration failed: Unified Diff at %s:\n\n%s\n"
                        % (rpath, "\n".join(rdiff)))


    def test_cutover_correctness(self):
        self._test_cutover(self.initial_servicedef, self.expected_servicedef)

    def test_cutover_idempotence(self):
        self._test_cutover(self.expected_servicedef, self.expected_servicedef)
