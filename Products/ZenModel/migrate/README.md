# Service Migrations

The [service migration SDK](https://github.com/control-center/service-migration/) provides
a programmatic way of making changes to service definitions.
These changes take the form of individual Migrate.Step classes, kept for now in ZenModel's migrate directory.

## Writing a new migration
Below is an example migration script:

``` python
# renameZopeToFoo.py

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class RenameZopeToFoo(Migrate.Step):
    """Rename zope service to Foo."""

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zopes = filter(lambda s: s.name == 'zope', ctx.services)
        commit = False
        for zope in zopes:
            commit = True
            zope.name = 'Foo'

        if commit:
            ctx.commit()

RenameZopeToFoo()
```

The basic steps of a migration script are:

    - Import servicemigration and set the required version
    - Define a new Migrate.Step subclass and set its version
    - Define the step's cutover method
        - Try to get a ServiceContext
        - Modify the services as they match some criteria
        - Commit if there were any changes
    - Instantiate the class once to register it with the Migrate framework


The SDK doesn't expose the servicedef directly, but instead uses an interface to make it easier to select and modify parts of the definition.
For one, most dictionaries are represented as lists. The key is an attribute of each value, typically `name`.
This is done even at the level of ServiceContext.services.

In general, the elements of a service definition are represented as class attributes, usually with a normalized name to keep with Python style and to avoid shadowing builtin names.


## Adding unit tests
Here's an example class that would test the above boilerplate migration:

``` python
# tests/test_RenameZopeToFoo.py

import os
import unittest

import Globals
import common


class Test_RenameZopeToFoo (unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that Zope is renamed to Foo.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-renameZopeToFoo.json'
    migration_module_name = 'renameZopeToFoo'
    migration_class_name = 'RenameZopeToFoo'

```

The migration scripts have a test class, ServiceMigrationTestCase, that provides the tools to test that a given script makes expected changes only if they're necessary.
It's important to note that ServiceMigrationTestCase itself is not a unittest.TestCase, so any test classes created must inherit from both SMTC and TestCase for them to be discovered by unittest.

There are four class attributes to define for a new Test\_something class: `initial_servicedef`, `expected_servicedef`, `migration_module_name`, and `migration_class_name`.
These values are used in the two test functions in ServiceMigrationTestCase.
The servicedef values refer to example service definitions stored in the tests directory.
Feel free to reuse `zenoss-resmgr-5.0.6_1.json` as an initial state, and to add new definitions to the same directory as needed.

The ServiceMigrationTestCase class defines two tests: `test_cutover_correctness` and `test_cutover_idempotence`.
The first tests that applying the named migration script on `initial_servicedef` results in the `expected_servicedef`, while the second test verifies that applying the migration on `expected_servicedef` has no effect.


## Running unit tests
As these are unittest TestCases, they can be discovered and run via `python -m unittest discover`.
Any additional `test_*` functions added to the class will also be discovered and run by unittest.

The service migration tests have also been added to zendev, so they can be invoked with `zendev test --zenoss-devimg unit Products.ZenModel.migrate`.
