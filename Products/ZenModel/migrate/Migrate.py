###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''Migrate

A small framework for data migration.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import Globals
import transaction
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Version import Version as VersionBase
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.Utils import zenPath
from Products.ZenModel.ZVersion import VERSION

import sys
import logging
import operator
from textwrap import wrap
log = logging.getLogger("zen.migrate")

allSteps = []

class MigrationFailed(Exception): pass

class Version(VersionBase):
    def __init__(self, *args, **kw):
        VersionBase.__init__(self, 'Zenoss', *args, **kw)

def cleanup():
    "recursively remove all files ending with .pyc"
    import os
    count = 0
    for p, d, fs in os.walk(zenPath('Products')):
        for f in fs: 
            if f.endswith('.pyc'):
                fullPath = os.path.join(p, f)
                os.remove(fullPath)
                count += 1
    log.debug('removed %d .pyc files from Products' % count)


class Step:
    'A single migration step, to be subclassed for each new change'

    # Every subclass should set this so we know when to run it
    version = -1
    dependencies = None


    def __init__(self):
        "self insert ourselves in the list of all steps"
        allSteps.append(self)

    def __cmp__(self, other):
        result = cmp(self.version, other.version)
        if result:
            return result
        # if we're in the other dependency list, we are "less"
        if self in other.getDependencies():
            return -1
        # if other is in the out dependency list, we are "greater"
        if other in self.getDependencies():
            return 1
        return 0

    def getDependencies(self):
        if not self.dependencies:
            return []
        result = []
        for d in self.dependencies:
            if d is not self:
                result.append(d)
                result.extend(d.getDependencies())
            else:
                log.error("Circular dependency among migration Steps: "
                          "%s is listed as a dependency of %s ",
                          self.name(), d.name())
        return result

    def prepare(self):
        "do anything you must before running the cutover"
        pass

    def cutover(self, dmd):
        "perform changes to the database"
        raise NotImplementedError

    def cleanup(self):
        "remove any intermediate results"
        pass

    def revert(self):
        pass

    def name(self):
        return self.__class__.__name__

    def isVersionAppropriate(self, version=None):
        """
        Return True if this step is appropriate for the given version of
        Zenoss, False otherwise.  Appropiate in this case means that the
        major and minor versions match.  version can be either a Version
        instance or a string.  If version is None then the version from
        ZVersion is used.
        """
        if version is None:
            version = VersionBase.parse(' Zenoss ' + VERSION)
        elif isinstance(version, basestring):
            version = VersionBase.parse(version)
        elif not isinstance(version, VersionBase):
            raise Exception('version for Step.isVersionAppropriate() must '
                            'be a string or an instance of VersionBase.')
        if self.version.major ==  version.major:
            if self.version.minor == version.minor:
                return True
            if version.micro >= 70 and version.minor + 1 == self.version.minor:
                return True
        return False


class Migration(ZenScriptBase):
    "main driver for migration: walks the steps and performs commit/abort"

    useDatabaseVersion = True

    def __init__(self):
        ZenScriptBase.__init__(self, connect=False)
        self.connect()
        self.allSteps = allSteps[:]
        self.allSteps.sort(lambda x,y: cmp(x.name(), y.name()))
        self.allSteps.sort()

    def message(self, msg):
        log.info(msg)

    def _currentVersion(self):
        if not hasattr(self.dmd, 'version') or not self.dmd.version:
            self.dmd.version = 'Zenoss ' + VERSION
        if type(self.dmd.version) == type(1.0):
            self.dmd.version = "Zenoss 0.%f" % self.dmd.version
        v = VersionBase.parse(self.dmd.version)
        v.name = 'Zenoss'
        return v

    def migrate(self):
        "walk the steps and apply them"
        steps = self.allSteps[:]
        
        # check version numbers
        while steps and steps[0].version < 0:
            raise MigrationFailed("Migration %s does not set "
                                  "the version number" %
                                  steps[0].__class__.__name__)

        # dump old steps        
        current = self._currentVersion()
        if self.useDatabaseVersion:
            op = self.options.again and operator.ge or operator.gt
            steps = [s for s in steps if op(s.version, current)]

        # Ideally migrate scripts are always run using the version of the code
        # that corresponds to the version in the migrate step.  Problems can
        # arise when executing migrate steps using newer code than that for
        # which they were intended.  See #2924
        if not self.options.force:
            inappropriate = [s for s in steps if not s.isVersionAppropriate()]
            if inappropriate:
                sys.stderr.write('The following migrate steps were not '
                        'intended to run with the currently installed version '
                        'of the Zenoss code.  The installed version is %s.\n ' 
                        % VERSION +
                        'You can override this warning with the --force '
                        'option.\n'
                        )
                for step in inappropriate:
                    sys.stderr.write('  %s (%s)\n'
                                    % (step.name(), step.version.short()))
                sys.exit(-1)

        for m in steps:
            m.prepare()

        for m in steps:
            if m.version > current:
                self.message("Database going to version %s" % m.version.long())
            self.message('Installing %s' % m.name())
            m.cutover(self.dmd)
            if m.version > current:
                self.dmd.version = m.version
        if type(self.dmd.version) != type(''):
            self.dmd.version = self.dmd.version.long()

        for m in steps:
            m.cleanup()

        cleanup()

        if not self.options.steps:
            rl = ReportLoader(noopts=True, app=self.app)
            rl.options.force = True
            rl.loadDatabase()


    def cutover(self):
        '''perform the migration, applying all the new steps,
        recovering on error'''
        self.backup()
        try:
            self.migrate()
            self.success()
        except Exception, ex:
            self.error("Recovering")
            self.recover()
            raise


    def error(self, msg):
        print >>sys.stderr, msg


    def backup(self):
        pass


    def recover(self):
        transaction.abort()
        steps = self.allSteps[:]
        current = self._currentVersion()
        while steps and steps[0].version < current:
            steps.pop(0)
        for m in steps:
            m.revert()


    def success(self):
        if self.options.commit:
            self.message('committing')
            transaction.commit()
        else:
            self.message('rolling back changes')
            self.recover()
        self.message("Migration successful")


    def parseOptions(self):
        ZenScriptBase.parseOptions(self)
        if self.args:
            if self.args == ['run']:
                sys.stderr.write('Use of "run" is depracated.\n')
            elif self.args == ['help']:
                sys.stderr.write('Use of "help" is depracated,'
                                    'use --help instead.\n')
                self.parser.print_help()
                self.parser.exit()
            elif self.args[0]:
                self.parser.error('Unrecognized option(s): %s\n' %
                    ', '.join(self.args) +
                    'Use --help for list of options.\n')


    def buildOptions(self):
        self.parser.add_option('--step',
                               action='append',
                               dest="steps",
                               help="Run the given step")
        # NB: The flag for this setting indicates a false value for the setting.
        self.parser.add_option('--dont-commit',
                               dest="commit",
                               action='store_false',
                               default=True,
                               help="Don't commit changes to the database")
        self.parser.add_option('--list',
                               action='store_true',
                               default=False,
                               dest="list",
                               help="List all the steps")
        self.parser.add_option('--level',
                               dest="level",
                               type='string',
                               default=None,
                               help="Run the steps by version number")
        self.parser.add_option('--again',
                                dest='again',
                                action='store_true',
                                default=False,
                                help='Rerun steps for current database '
                                        'version.')
        self.parser.add_option('--force',
                                dest='force',
                                action='store_true',
                                default=False,
                                help='Force version inappropriate migrate '
                                        'steps to run.')
        ZenScriptBase.buildOptions(self)


    def orderedSteps(self):
        return self.allSteps

    def list(self):
        print ' Ver      Name        Description'
        print '-----+---------------+-----------' + '-'*40
        for s in self.allSteps:
            doc = s.__doc__
            if not doc:
                doc = sys.modules[s.__class__.__module__].__doc__ or 'Not Documented'
                doc.strip()
            indent = ' '*22
            doc = '\n'.join(wrap(doc, width=80,
                                 initial_indent=indent,
                                 subsequent_indent=indent))
            doc = doc.lstrip()
            print "%-8s %-15s %s" % (s.version.short(), s.name(), doc)

    def main(self):
        if self.options.list:
            self.list()
            return
                
        if self.options.level is not None:
            self.options.level = VersionBase.parse('Zenoss ' + self.options.level)
            self.allSteps = [s for s in self.allSteps
                             if s.version == self.options.level]
            self.useDatabaseVersion = False
        if self.options.steps:
            import re
            def matches(name):
                for step in self.options.steps:
                    if re.match('.*' + step + '.*', name):
                        return True
                return False
            self.allSteps = [s for s in self.allSteps if matches(s.name())]
            if not self.allSteps:
                log.error('No steps matching %s found' % self.options.steps)
                return
            self.useDatabaseVersion = False
        log.debug("Level %s, steps = %s",
                  self.options.level, self.options.steps)
        self.cutover()
