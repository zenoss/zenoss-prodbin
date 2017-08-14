# Migrations

# Table of Contents
  - [Overview](#overview)
    - [Model Migrations](#model-migrations)
    - [ Service Migrations](#service-migrations)
      - [Writing a new migration](#writing-a-new-migration)
      - [Adding unit tests](#adding-unit-tests)
    - [Managing Migrate.Version](managing-migrate.version)
      - [Starting a new release](#starting-a-new-release)
      - [Working with SCHEMA versions](#working-with-schema-versions)
      - [Release Process](#release-process)
    - [Running unit tests](#running-unit-tests)
      - [Running a migration manually](#running-a-migration-manually)

# Overview

There are 2 types of migrations, both of which are discussed below

## Model Migrations

These are migrations that affect the Zenoss model database, and possibly other zenoss-specific components.
```
TODO: Expand on this.
```

## Service Migrations

The [service migration SDK](https://github.com/control-center/service-migration/) provides
a programmatic way of making changes to service definitions.
These changes take the form of individual Migrate.Step classes, kept for now in ZenModel's migrate directory.

### Writing a new migration
Below is an example migration script:

``` python
# renameZopeToFoo.py

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.0.0")

class RenameZopeToFoo(Migrate.Step):
    """Rename zope service to Foo."""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

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


## Managing Migrate.Version

`Migrate.Version()` is used by the upgrade framework to control which migrations
are executed when a particular version of Zenoss is upgraded.  The basic idea is
that the `upgrade` command for the Zope service will execute all of the
migrations with a value greater than the current value stored in Zope. Upon
successful completion of the upgrade, the value of the highest migration script
is then stored in the database.

In order to better manage the values used across a range of different releases,
we have implemented a semi-automated scheme to minimize the process of manually
specifying different values for `Migrate.Version()`.

### Starting a new release
At the start of a new release, the toplevel makefile should be updated to set
the values of SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION to the appropriate
versions for that release.

Each new migration script added for that release should set `Migrate.Version()`
as follows:

```
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
...
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)
```

### Working with SCHEMA versions

The regular `make` process for prodbin, as well as `zendev devimg` and `zendev test`
will invoke the make target `generate-zversion` which will build ZMigrateVersion.py from ZMigrateVersion.py.in
using the values of SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION defined in the
toplevel makefile.  In this way, developers working on a new release do not need
to specify explicit versions - they can rely on the build process to inject values
for a given release.  By the same token, changes can be backported to earlier
releases without working about which versions to use for different releases because
the toplevel makefile in each release should define the values unique to that release.

### Release Process

As one of the final steps in the release process, someone must run `make replace-zmigrateversion`
which will edit all of the files in Products/ZenModel/migrate, replacing the variables
SCHEMA_MAJOR, SCHEMA_MINOR, & SCHEMA_REVISION with the versions defined in the makefile.

Those changes can be verified with `make verify-explicit-zmigrateversion:` which will fail
if any files were overlooked.  If `make replace-zmigrateversion` was unable to update
the a version for some unexpected reason, the migration script can be changed manually
if necessary at this stage.

After the migration scripts have been updated, then they must be checked into git before
executing the git-flow-release process.


### Adding unit tests
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

The service migration tests have also been added to zendev. In the original version of zendev (circa RM 5.0 and 5.1), the tests can be invoked with `zendev test unit Products.ZenModel.migrate`.  In later versions (circa RM 5.2 and higher), the tests can be invoked with `zendev test -- --type=unit --name=Products.ZenModel.migrate -v`

Guidelines for running RM unit-test in general (not just service migrations) is available in the zendev [README](https://github.com/zenoss/zendev/tree/zendev2#testing-with-devimg).

### Running a migration manually

Instructions for running a migration manually are available on the engineering site [here](https://sites.google.com/a/zenoss.com/engineering/home/faq/work-with-rm/howtorunzenmigrate).

