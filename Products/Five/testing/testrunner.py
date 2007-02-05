##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test runner

$Id: testrunner.py 60620 2005-10-21 18:07:37Z yuppie $
"""

# Too bad: For now, we depend on Products.Five.testing.  This is because
# we want to use the latest, greatest doctest, which Products.Five.testing
# provides.  Then again, Products.Five.testing is generally useful.
import gc
import glob
import logging
import optparse
import os
import pdb
import re
import sys
import tempfile
import threading
import time
import trace
import traceback
import unittest
import hotshot
import hotshot.stats

real_pdb_set_trace = pdb.set_trace

class MyIgnore(trace.Ignore):
    def names(self, filename, modulename):
        if modulename in self._ignore:
            return self._ignore[modulename]

        if filename.startswith('<doctest'):
            self._ignore[modulename] = True

        return trace.Ignore.names(self, filename, modulename)


class MyTrace(trace.Trace):
    def __init__(self, *args, **kws):
        trace.Trace.__init__(self, *args, **kws)
        self.ignore = MyIgnore(kws['ignoremods'], kws['ignoredirs'])
        self.started = False

    def start(self):
        assert not self.started, "can't start if already started"
        if not self.donothing:
            sys.settrace(self.globaltrace)
            threading.settrace(self.globaltrace)
        self.started = True

    def stop(self):
        assert self.started, "can't stop if not started"
        if not self.donothing:
            sys.settrace(None)
            threading.settrace(None)
        self.starte = False


class EndRun(Exception):
    """Indicate that the existing run call should stop

    Used to prevent additional test output after post-mortem debugging.
    """

def run(defaults=None, args=None):
    if args is None:
        args = sys.argv

    # Control reporting flags during run
    old_reporting_flags = doctest.set_unittest_reportflags(0)

    # Check to see if we are being run as a subprocess. If we are,
    # then use the resume-layer and defaults passed in.
    if len(args) > 1 and args[1] == '--resume-layer':
        args.pop(1)
        resume_layer = args.pop(1)
        defaults = []
        while len(args) > 1 and args[1] == '--default':
            args.pop(1)
            defaults.append(args.pop(1))

        sys.stdin = FakeInputContinueGenerator()
    else:
        resume_layer = None

    options = get_options(args, defaults)
    options.testrunner_defaults = defaults
    options.resume_layer = resume_layer

    # Make sure we start with real pdb.set_trace.  This is needed
    # to make tests of the test runner work properly. :)
    pdb.set_trace = real_pdb_set_trace

    if options.profile and sys.version_info[:3] <= (2,4,1) and __debug__:
        print ('Because of a bug in Python < 2.4.1, profiling '
               'during tests requires the -O option be passed to '
               'Python (not the test runner).')
        sys.exit()

    if options.coverage:
        tracer = MyTrace(ignoredirs=[sys.prefix, sys.exec_prefix],
                         ignoremods=["os", "posixpath", "stat"],
                         trace=False, count=True)
        tracer.start()
    else:
        tracer = None

    if options.profile:
        prof_prefix = 'tests_profile.'
        prof_suffix = '.prof'
        prof_glob = prof_prefix + '*' + prof_suffix

        # if we are going to be profiling, and this isn't a subprocess,
        # clean up any stale results files
        if not options.resume_layer:
            for file_name in glob.glob(prof_glob):
                os.unlink(file_name)
        
        # set up the output file
        dummy, file_path = tempfile.mkstemp(prof_suffix, prof_prefix, '.')
        prof = hotshot.Profile(file_path)
        prof.start()

    try:
        try:
            failed = run_with_options(options)
        except EndRun:
            failed = True
    finally:
        if tracer:
            tracer.stop()
        if options.profile:                         
            prof.stop()
            prof.close()

    if options.profile and not options.resume_layer:
        stats = None
        for file_name in glob.glob(prof_glob):
            loaded = hotshot.stats.load(file_name)
            if stats is None:
                stats = loaded
            else:
                stats.add(loaded)
        stats.sort_stats('cumulative', 'calls')
        stats.print_stats(50)

    if tracer:
        coverdir = os.path.join(os.getcwd(), options.coverage)
        r = tracer.results()
        r.write_results(summary=True, coverdir=coverdir)

    doctest.set_unittest_reportflags(old_reporting_flags)

    return failed

def run_with_options(options):

    if options.resume_layer:
        original_stderr = sys.stderr
        sys.stderr = sys.stdout
    elif options.verbose:
        if options.all:
            print "Running tests at all levels"
        else:
            print "Running tests at level %d" % options.at_level


    # XXX add tracing later

    # Add directories to the path
    for path in options.path:
        if path not in sys.path:
            sys.path.append(path)

    remove_stale_bytecode(options)

    configure_logging()

    tests_by_layer_name = find_tests(options)

    ran = 0
    failures = []
    errors = []
    nlayers = 0
    import_errors = tests_by_layer_name.pop(None, None)

    if import_errors:
        print "Test-module import failures:"
        for error in import_errors:
            print_traceback("Module: %s\n" % error.module, error.exc_info),
        print


    if 'unit' in tests_by_layer_name:
        tests = tests_by_layer_name.pop('unit')
        if (not options.non_unit) and not options.resume_layer:
            if options.layer:
                should_run = False
                for pat in options.layer:
                    if pat('unit'):
                        should_run = True
                        break
            else:
                should_run = True

            if should_run:
                print "Running unit tests:"
                nlayers += 1
                ran += run_tests(options, tests, 'unit', failures, errors)

    if options.resume_layer:
        resume = False
    else:
        resume = True

    setup_layers = {}
    for layer_name, layer, tests in ordered_layers(tests_by_layer_name):
        if options.layer:
            should_run = False
            for pat in options.layer:
                if pat(layer_name):
                    should_run = True
                    break
        else:
            should_run = True

        if should_run:
            if (not resume) and (layer_name == options.resume_layer):
                resume = True
            if not resume:
                continue
            nlayers += 1
            try:
                ran += run_layer(options, layer_name, layer, tests,
                                 setup_layers, failures, errors)
            except CanNotTearDown:
                setup_layers = None
                ran += resume_tests(options, layer_name, failures, errors)
                break

    if setup_layers:
        print "Tearing down left over layers:"
        tear_down_unneeded((), setup_layers, True)

    if options.resume_layer:
        sys.stdout.close()
        print >> original_stderr, ran, len(failures), len(errors)
        for test, exc_info in failures:
            print >> original_stderr, ' '.join(str(test).strip().split('\n'))
        for test, exc_info in errors:
            print >> original_stderr, ' '.join(str(test).strip().split('\n'))

    else:
        if options.verbose > 1:
            if errors:
                print
                print "Tests with errors:"
                for test, exc_info in errors:
                    print "  ", test

            if failures:
                print
                print "Tests with failures:"
                for test, exc_info in failures:
                    print "  ", test

        if nlayers != 1:
            print "Total: %s tests, %s failures, %s errors" % (
                ran, len(failures), len(errors))

        if import_errors:
            print
            print "Test-modules with import problems:"
            for test in import_errors:
                print "  " + test.module


    return bool(import_errors or failures or errors)

def run_tests(options, tests, name, failures, errors):
    repeat = options.repeat or 1
    ran = 0
    tests._tests = [t for t in tests._tests if t is not None] # scrub 'em
    for i in range(repeat):
        if repeat > 1:
            print "Iteration", i+1

        if options.verbose > 0 or options.progress:
            print '  Running:'
        if options.verbose == 1 and not options.progress:
            print '    ',
        result = TestResult(options, tests)
        t = time.time()


        if options.post_mortem:
            # post-mortem debugging
            for test in tests:
                result.startTest(test)
                try:
                    try:
                        test.debug()
                    except:
                        result.addError(
                            test,
                            sys.exc_info()[:2] + (sys.exc_info()[2].tb_next, ),
                            )
                    else:
                        result.addSuccess(test)
                finally:
                    result.stopTest(test)

        else:
            # normal
            tests(result)

        t = time.time() - t
        if options.verbose == 1 or options.progress:
            print
        failures.extend(result.failures)
        errors.extend(result.errors)
        print (
            "  Ran %s tests with %s failures and %s errors in %.3f seconds." %
            (result.testsRun, len(result.failures), len(result.errors), t)
            )
        ran += result.testsRun

    return ran

def run_layer(options, layer_name, layer, tests, setup_layers,
              failures, errors):
    print "Running %s tests:" % layer_name

    gathered = []
    gather_layers(layer, gathered)
    needed = dict([(l, 1) for l in gathered])
    tear_down_unneeded(needed, setup_layers)

    setup_layer(layer, setup_layers)
    return run_tests(options, tests, layer_name, failures, errors)

def resume_tests(options, layer_name, failures, errors):
    args = [sys.executable,
            options.original_testrunner_args[0],
            '--resume-layer', layer_name,
            ]
    for d in options.testrunner_defaults:
        args.extend(['--default', d])

    args.extend(options.original_testrunner_args[1:])

    if sys.platform.startswith('win'):
        args = args[0] + ' ' + ' '.join([
            ('"' + a.replace('\\', '\\\\').replace('"', '\\"') + '"')
            for a in args[1:]
            ])

    # this is because of a bug in Python (http://www.python.org/sf/900092)
    if options.profile and sys.version_info[:3] <= (2,4,1):
        args.insert(1, '-O')

    subin, subout, suberr = os.popen3(args)
    for l in subout:
        sys.stdout.write(l)

    line = suberr.readline()
    try:
        ran, nfail, nerr = map(int, line.strip().split())
    except:
        raise SubprocessError(line+suberr.read())

    while nfail > 0:
        nfail -= 1
        failures.append((suberr.readline().strip(), None))
    while nerr > 0:
        nerr -= 1
        errors.append((suberr.readline().strip(), None))
    return ran


class SubprocessError(Exception):
    """An error occurred when running a subprocess
    """

class CanNotTearDown(Exception):
    "Couldn't tear down a test"

def tear_down_unneeded(needed, setup_layers, optional=False):
    # Tear down any layers not needed for these tests. The unneeded
    # layers might interfere.
    unneeded = [l for l in setup_layers if l not in needed]
    unneeded = order_by_bases(unneeded)
    unneeded.reverse()
    for l in unneeded:
        print "  Tear down %s" % name_from_layer(l),
        t = time.time()
        try:
            l.tearDown()
        except NotImplementedError:
            print "... not supported"
            if not optional:
                raise CanNotTearDown(l)
        else:
            print "in %.3f seconds." % (time.time() - t)
        del setup_layers[l]

def setup_layer(layer, setup_layers):
    if layer not in setup_layers:
        for base in layer.__bases__:
            setup_layer(base, setup_layers)
        print "  Set up %s.%s" % (layer.__module__, layer.__name__),
        t = time.time()
        layer.setUp()
        print "in %.3f seconds." % (time.time() - t)
        setup_layers[layer] = 1

def dependencies(bases, result):
    for base in bases:
        result[base] = 1
        dependencies(base.__bases__, result)



class TestResult(unittest.TestResult):

    def __init__(self, options, tests):
        unittest.TestResult.__init__(self)
        self.options = options
        if options.progress:
            count = 0
            for test in tests:
                count += test.countTestCases()
            self.count = count
        self.last_width = 0

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        testsRun = self.testsRun - 1
        count = test.countTestCases()
        self.testsRun = testsRun + count
        options = self.options
        self.test_width = 0

        if options.progress:
            s = "    %d/%d (%.1f%%)" % (
                self.testsRun, self.count,
                (self.testsRun) * 100.0 / self.count
                )
            sys.stdout.write(s)
            self.test_width += len(s)

        elif options.verbose == 1:
            for i in range(count):
                sys.stdout.write('.')
                testsRun += 1
                if (testsRun % 50) == 0:
                    print
                    print '    ',
        elif options.verbose > 1:
            print '   ',

        if options.verbose > 1:
            s = str(test)
            sys.stdout.write(' ')
            sys.stdout.write(s)
            self.test_width += len(s) + 1

        sys.stdout.flush()

        self._threads = threading.enumerate()
        self._start_time = time.time()

    def addSuccess(self, test):
        if self.options.verbose > 2:
            t = max(time.time() - self._start_time, 0.0)
            s = " (%.3f ms)" % t
            sys.stdout.write(s)
            self.test_width += len(s) + 1

    def addError(self, test, exc_info):
        if self.options.verbose > 2:
            print " (%.3f ms)" % (time.time() - self._start_time)

        unittest.TestResult.addError(self, test, exc_info)
        print
        self._print_traceback("Error in test %s" % test, exc_info)

        if self.options.post_mortem:
            if self.options.resume_layer:
                print
                print '*'*70
                print ("Can't post-mortem debug when running a layer"
                       " as a subprocess!")
                print '*'*70
                print
            else:
                post_mortem(exc_info)

        self.test_width = self.last_width = 0

    def addFailure(self, test, exc_info):


        if self.options.verbose > 2:
            print " (%.3f ms)" % (time.time() - self._start_time)

        unittest.TestResult.addFailure(self, test, exc_info)
        print
        self._print_traceback("Failure in test %s" % test, exc_info)

        if self.options.post_mortem:
            post_mortem(exc_info)

        self.test_width = self.last_width = 0


    def stopTest(self, test):
        if self.options.progress:
            sys.stdout.write(' ' * (self.last_width - self.test_width) + "\r")
            self.last_width = self.test_width
        elif self.options.verbose > 1:
            print

        if gc.garbage:
            print "The following test left garbage:"
            print test
            print gc.garbage
            # TODO: Perhaps eat the garbage here, so that the garbage isn't
            #       printed for every subsequent test.

        # Did the test leave any new threads behind?
        new_threads = [t for t in threading.enumerate()
                         if (t.isAlive()
                             and
                             t not in self._threads)]
        if new_threads:
            print "The following test left new threads behind:"
            print test
            print "New thread(s):", new_threads

        sys.stdout.flush()


    def _print_traceback(self, msg, exc_info):
        print_traceback(msg, exc_info)

doctest_template = """
File "%s", line %s, in %s

%s
Want:
%s
Got:
%s
"""

class FakeInputContinueGenerator:

    def readline(self):
        print  'c\n'
        print '*'*70
        print ("Can't use pdb.set_trace when running a layer"
               " as a subprocess!")
        print '*'*70
        print
        return 'c\n'


def print_traceback(msg, exc_info):
    print
    print msg

    v = exc_info[1]
    if isinstance(v, doctest.DocTestFailureException):
        tb = v.args[0]
    elif isinstance(v, doctest.DocTestFailure):
        tb = doctest_template % (
            v.test.filename,
            v.test.lineno + v.example.lineno + 1,
            v.test.name,
            v.example.source,
            v.example.want,
            v.got,
            )
    else:
        tb = "".join(traceback.format_exception(*exc_info))

    print tb

def post_mortem(exc_info):
    err = exc_info[1]
    if isinstance(err, (doctest.UnexpectedException, doctest.DocTestFailure)):

        if isinstance(err, doctest.UnexpectedException):
            exc_info = err.exc_info

            # Print out location info if the error was in a doctest
            if exc_info[2].tb_frame.f_code.co_filename == '<string>':
                print_doctest_location(err)

        else:
            print_doctest_location(err)
            # Hm, we have a DocTestFailure exception.  We need to
            # generate our own traceback
            try:
                exec ('raise ValueError'
                      '("Expected and actual output are different")'
                      ) in err.test.globs
            except:
                exc_info = sys.exc_info()

    print "%s:" % (exc_info[0], )
    print exc_info[1]
    pdb.post_mortem(exc_info[2])
    raise EndRun

def print_doctest_location(err):
    # This mimicks pdb's output, which gives way cool results in emacs :)
    filename = err.test.filename
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    print "> %s(%s)_()" % (filename, err.test.lineno+err.example.lineno+1)

def ordered_layers(tests_by_layer_name):
    layer_names = dict([(layer_from_name(layer_name), layer_name)
                        for layer_name in tests_by_layer_name])
    for layer in order_by_bases(layer_names):
        layer_name = layer_names[layer]
        yield layer_name, layer, tests_by_layer_name[layer_name]

def gather_layers(layer, result):
    result.append(layer)
    for b in layer.__bases__:
        gather_layers(b, result)

def layer_from_name(layer_name):
    layer_names = layer_name.split('.')
    layer_module, module_layer_name = layer_names[:-1], layer_names[-1]
    return getattr(import_name('.'.join(layer_module)), module_layer_name)

def order_by_bases(layers):
    """Order the layers from least to most specific (bottom to top)
    """
    named_layers = [(name_from_layer(layer), layer) for layer in layers]
    named_layers.sort()
    named_layers.reverse()
    gathered = []
    for name, layer in named_layers:
        gather_layers(layer, gathered)
    gathered.reverse()
    seen = {}
    result = []
    for layer in gathered:
        if layer not in seen:
            seen[layer] = 1
            if layer in layers:
                result.append(layer)
    return result

def name_from_layer(layer):
    return layer.__module__ + '.' + layer.__name__

def find_tests(options):
    suites = {}
    for suite in find_suites(options):
        for test, layer_name in tests_from_suite(suite, options):
            suite = suites.get(layer_name)
            if not suite:
                suite = suites[layer_name] = unittest.TestSuite()
            suite.addTest(test)
    return suites

def tests_from_suite(suite, options, dlevel=1, dlayer='unit'):
    level = getattr(suite, 'level', dlevel)
    layer = getattr(suite, 'layer', dlayer)
    if not isinstance(layer, basestring):
        layer = layer.__module__ + '.' + layer.__name__

    if isinstance(suite, unittest.TestSuite):
        for possible_suite in suite:
            for r in tests_from_suite(possible_suite, options, level, layer):
                yield r
    elif isinstance(suite, StartUpFailure):
        yield (suite, None)
    else:
        if level <= options.at_level:
            for pat in options.test:
                if pat(str(suite)):
                    yield (suite, layer)
                    break

def find_suites(options):
    for fpath in find_test_files(options):
        for prefix in options.prefix:
            if fpath.startswith(prefix):
                # strip prefix, strip .py suffix and convert separator to dots
                module_name = fpath[len(prefix):-3].replace(os.path.sep, '.')
                try:
                    module = import_name(module_name)
                except:
                    suite = StartUpFailure(
                        options, module_name,
                        sys.exc_info()[:2]
                        + (sys.exc_info()[2].tb_next.tb_next,),
                        )
                else:
                    try:
                        suite = getattr(module, options.suite_name)()
                    except:
                        suite = StartUpFailure(
                            options, module_name, sys.exc_info()[:2]+(None,))

                yield suite
                break

class StartUpFailure:

    def __init__(self, options, module, exc_info):
        if options.post_mortem:
            post_mortem(exc_info)
        self.module = module
        self.exc_info = exc_info

def find_test_files(options):
    found = {}
    for f in find_test_files_(options):
        for filter in options.module:
            if filter(f):
                if f not in found:
                    found[f] = 1
                    yield f
                    break

identifier = re.compile('^[_a-zA-Z][_a-zA-Z0-9]+$').match
def find_test_files_(options):
    tests_pattern = options.tests_pattern
    test_file_pattern = options.test_file_pattern
    for p in test_dirs(options, {}):
        for dirname, dirs, files in walk_with_symlinks(options, p):
            if (dirname != p) and ('__init__.py' not in files):
                continue
            dirs[:] = filter(identifier, dirs)
            d = os.path.split(dirname)[1]
            if tests_pattern(d) and ('__init__.py' in files):
                # tests directory
                for file in files:
                    if file.endswith('.py') and test_file_pattern(file[:-3]):
                        f = os.path.join(dirname, file)
                        yield f

            for file in files:
                if file.endswith('.py') and tests_pattern(file[:-3]):
                    f = os.path.join(dirname, file)
                    yield f


def walk_with_symlinks(options, dir):
    # TODO -- really should have test of this that uses symlinks
    #         this is hard on a number of levels ...
    for dirpath, dirs, files in os.walk(dir):
        dirs.sort()
        files.sort()
        dirs[:] = [d for d in dirs if d not in options.ignore_dir]
        yield (dirpath, dirs, files)
        for d in dirs:
            p = os.path.join(dirpath, d)
            if os.path.islink(p):
                for sdirpath, sdirs, sfiles in walk_with_symlinks(options, p):
                    yield (sdirpath, sdirs, sfiles)

compiled_sufixes = '.pyc', '.pyo'
def remove_stale_bytecode(options):
    if options.keepbytecode:
        return
    for p in options.path:
        for dirname, dirs, files in walk_with_symlinks(options, p):
            for file in files:
                if file[-4:] in compiled_sufixes and file[:-1] not in files:
                    fullname = os.path.join(dirname, file)
                    print "Removing stale bytecode file", fullname
                    os.unlink(fullname)


def test_dirs(options, seen):
    if options.package:
        for p in options.package:
            p = import_name(p)
            for p in p.__path__:
                p = os.path.abspath(p)
                if p in seen:
                    continue
                for prefix in options.prefix:
                    if p.startswith(prefix):
                        seen[p] = 1
                        yield p
                        break
    else:
        for dpath in options.path:
            yield dpath


def import_name(name):
    __import__(name)
    return sys.modules[name]

def configure_logging():
    """Initialize the logging module."""
    import logging.config

    # Get the log.ini file from the current directory instead of
    # possibly buried in the build directory.  TODO: This isn't
    # perfect because if log.ini specifies a log file, it'll be
    # relative to the build directory.  Hmm...  logini =
    # os.path.abspath("log.ini")

    logini = os.path.abspath("log.ini")
    if os.path.exists(logini):
        logging.config.fileConfig(logini)
    else:
        # If there's no log.ini, cause the logging package to be
        # silent during testing.
        root = logging.getLogger()
        root.addHandler(NullHandler())
        logging.basicConfig()

    if os.environ.has_key("LOGGING"):
        level = int(os.environ["LOGGING"])
        logging.getLogger().setLevel(level)

class NullHandler(logging.Handler):
    """Logging handler that drops everything on the floor.

    We require silence in the test environment.  Hush.
    """

    def emit(self, record):
        pass



###############################################################################
# Command-line UI

parser = optparse.OptionParser("Usage: %prog [options] [MODULE] [TEST]")

######################################################################
# Searching and filtering

searching = optparse.OptionGroup(parser, "Searching and filtering", """\
Options in this group are used to define which tests to run.
""")

searching.add_option(
    '--package', '--dir', '-s', action="append", dest='package',
    help="""\
Search the given package's directories for tests.  This can be
specified more than once to run tests in multiple parts of the source
tree.  For example, if refactoring interfaces, you don't want to see
the way you have broken setups for tests in other packages. You *just*
want to run the interface tests.

Packages are supplied as dotted names.  For compatibility with the old
test runner, forward and backward slashed in package names are
converted to dots.

(In the special case of packages spread over multiple directories,
only directories within the test search path are searched. See the
--path option.)

""")

searching.add_option(
    '--module', '-m', action="append", dest='module',
    help="""\
Specify a test-module filter as a regular expression.  This is a
case-sensitive regular expression, used in search (not match) mode, to
limit which test modules are searched for tests.  In an extension of
Python regexp notation, a leading "!" is stripped and causes the sense
of the remaining regexp to be negated (so "!bc" matches any string
that does not match "bc", and vice versa).  The option can be
specified multiple test-module filters.  Test modules matching any of
the test filters are searched.  If no test-module filter is specified,
then all test moduless are used.
""")

searching.add_option(
    '--test', '-t', action="append", dest='test',
    help="""\
Specify a test filter as a regular expression.  This is a
case-sensitive regular expression, used in search (not match) mode, to
limit which tests are run.  In an extension of Python regexp notation,
a leading "!" is stripped and causes the sense of the remaining regexp
to be negated (so "!bc" matches any string that does not match "bc",
and vice versa).  The option can be specified multiple test filters.
Tests matching any of the test filters are included.  If no test
filter is specified, then all tests are run.
""")

searching.add_option(
    '--unit', '-u', action="store_true", dest='unit',
    help="""\
Run only unit tests, ignoring any layer options.
""")

searching.add_option(
    '--non-unit', '-f', action="store_true", dest='non_unit',
    help="""\
Run tests other than unit tests.
""")

searching.add_option(
    '--layer', action="append", dest='layer',
    help="""\
Specify a test layer to run.  The option can be given multiple times
to specify more than one layer.  If not specified, all layers are run.
It is common for the running script to provide default values for this
option.  Layers are specified regular expressions, used in search
mode, for dotted names of objects that define a layer.  In an
extension of Python regexp notation, a leading "!" is stripped and
causes the sense of the remaining regexp to be negated (so "!bc"
matches any string that does not match "bc", and vice versa).  The
layer named 'unit' is reserved for unit tests, however, take note of
the --unit and non-unit options.
""")

searching.add_option(
    '-a', '--at-level', type='int', dest='at_level',
    help="""\
Run the tests at the given level.  Any test at a level at or below
this is run, any test at a level above this is not run.  Level 0
runs all tests.
""")

searching.add_option(
    '--all', action="store_true", dest='all',
    help="Run tests at all levels.")

parser.add_option_group(searching)

######################################################################
# Reporting

reporting = optparse.OptionGroup(parser, "Reporting", """\
Reporting options control basic aspects of test-runner output
""")

reporting.add_option(
    '--verbose', '-v', action="count", dest='verbose',
    help="""\
Increment the verbosity level.
""")

reporting.add_option(
    '--progress', '-p', action="store_true", dest='progress',
    help="""\
Output progress status
""")

def report_only_first_failure(*args):
    old = doctest.set_unittest_reportflags(0)
    doctest.set_unittest_reportflags(old | doctest.REPORT_ONLY_FIRST_FAILURE)

reporting.add_option(
    '-1', action="callback", callback=report_only_first_failure,
    help="""\
Report only the first failure in a doctest. (Examples after the
failure are still executed, in case they do any cleanup.)
""")

parser.add_option_group(reporting)

######################################################################
# Analysis

analysis = optparse.OptionGroup(parser, "Analysis", """\
Analysis options provide tools for analysing test output.
""")


analysis.add_option(
    '--post-mortem', '-D', action="store_true", dest='post_mortem',
    help="Enable post-mortem debugging of test failures"
    )


def gc_callback(option, opt, GC_THRESHOLD, *args):
    import gc
    if GC_THRESHOLD == 0:
        gc.disable()
        print "gc disabled"
    else:
        gc.set_threshold(GC_THRESHOLD)
        print "gc threshold:", gc.get_threshold()

analysis.add_option(
    '--gc', action="callback", callback=gc_callback, dest='gc', type="int",
    help="""\
Set the garbage collector generation0 threshold.  This can be used
to stress memory and gc correctness.  Some crashes are only
reproducible when the threshold is set to 1 (agressive garbage
collection).  Do "--gc 0" to disable garbage collection altogether.
""")

analysis.add_option(
    '--repeat', action="store", type="int", dest='repeat',
    help="""\
Repeat the testst the given number of times.  This option is used to
make sure that tests leave thier environment in the state they found
it and, with the --refcount option to look for memory leaks.
""")

def refcount_available(*args):
    if not hasattr(sys, "gettotalrefcount"):
        raise optparse.OptionValueError("""\
The Python you are running was not configured with --with-pydebug.
This is required to use the --refount option.
""")

analysis.add_option(
    '--refcount',
    action="callback", callback=refcount_available,
    dest='refcount',
    help="""\
After each run of the tests, output a report summarizing changes in
refcounts by object type.  This option that requires that Python was
built with the --with-pydebug option to configure.
""")

analysis.add_option(
    '--coverage', action="store", type='string', dest='coverage',
    help="""\
Perform code-coverage analysis, saving trace data to the directory
with the given name.  A code coverage summary is printed to standard
out.
""")

analysis.add_option(
    '--profile', action="store_true", dest='profile',
    help="""\
Run the tests under hotshot and display the top 50 stats, sorted by
cumulative time and number of calls.
""")

def do_pychecker(*args):
    if not os.environ.get("PYCHECKER"):
        os.environ["PYCHECKER"] = "-q"
    import pychecker.checker

analysis.add_option(
    '--pychecker', action="callback", callback=do_pychecker,
    help="""\
Run the tests under pychecker
""")

parser.add_option_group(analysis)

######################################################################
# Setup

setup = optparse.OptionGroup(parser, "Setup", """\
Setup options are normally supplied by the testrunner script, although
they can be overridden by users.
""")

setup.add_option(
    '--path', action="append", dest='path',
    help="""\
Specify a path to be added to Python's search path.  This option can
be used multiple times to specify multiple search paths.  The path is
usually specified by the test-runner script itself, rather than by
users of the script, although it can be overridden by users.  Only
tests found in the path will be run.
""")

setup.add_option(
    '--tests-pattern', action="store", dest='tests_pattern',
    help="""\
Specify the pattern for identifying tests modules. Tests modules are
packages containing test modules or modules containing tests.  When
searching for tests, the test runner looks for modules or packages
with this name.
""")

setup.add_option(
    '--suite-name', action="store", dest='suite_name',
    help="""\
Specify the name of the object in each test_module that contains the
module's test suite.
""")

setup.add_option(
    '--test-file-pattern', action="store", dest='test_file_pattern',
    help="""\
Specify the name of tests modules. Tests modules are packages
containing test files or modules containing tests.  When searching for
tests, the test runner looks for modules or packages with this name.
""")

setup.add_option(
    '--ignore_dir', action="append", dest='ignore_dir',
    help="""\
Specifies the name of a directory to ignore when looking for tests.
""")

parser.add_option_group(setup)

######################################################################
# Other

other = optparse.OptionGroup(parser, "Other", "Other options")

other.add_option(
    '--keepbytecode', '-k', action="store_true", dest='keepbytecode',
    help="""\
Normally, the test runner scans the test paths and the test
directories looking for and deleting pyc or pyo files without
corresponding py files.  This is to prevent spurious test failures due
to finding compiled moudules where source modules have been deleted.
This scan can be time consuming.  Using this option disables this
scan.  If you know you haven't removed any modules since last running
the tests, can make the test run go much faster.
""")

parser.add_option_group(other)

######################################################################
# Command-line processing

def compile_filter(pattern):
    if pattern.startswith('!'):
        pattern = re.compile(pattern[1:]).search
        return (lambda s: not pattern(s))
    return re.compile(pattern).search

def merge_options(options, defaults):
    odict = options.__dict__
    for name, value in defaults.__dict__.items():
        if (value is not None) and (odict[name] is None):
            odict[name] = value

default_setup_args = [
    '--tests-pattern', '^tests$',
    '--at-level', 1,
    '--ignore', '.svn',
    '--ignore', 'CVS',
    '--ignore', '{arch}',
    '--ignore', '.arch-ids',
    '--ignore', '_darcs',
    '--test-file-pattern', '^test',
    '--suite-name', 'test_suite',
    ]

def get_options(args=None, defaults=None):

    default_setup, _ = parser.parse_args(default_setup_args)
    assert not _
    if defaults:
        defaults, _ = parser.parse_args(defaults)
        assert not _
        merge_options(defaults, default_setup)
    else:
        defaults = default_setup

    if args is None:
        args = sys.argv
    original_testrunner_args = args
    args = args[1:]
    options, positional = parser.parse_args(args)
    merge_options(options, defaults)
    options.original_testrunner_args = original_testrunner_args

    if positional:
        module_filter = positional.pop()
        if module_filter != '.':
            if options.module:
                options.module.append(module_filter)
            else:
                options.module = [module_filter]

        if positional:
            test_filter = [positional]
            if options.test:
                options.test.append(test_filter)
            else:
                options.test = [test_filter]

    options.ignore_dir = dict([(d,1) for d in options.ignore_dir])
    options.test_file_pattern = re.compile(options.test_file_pattern).search
    options.tests_pattern = re.compile(options.tests_pattern).search
    options.test = map(compile_filter, options.test or ('.'))
    options.module = map(compile_filter, options.module or ('.'))

    if options.package:
        options.package = [p.replace('/', '.').replace('\\', '.')
                           for p in options.package]
    options.path = map(os.path.abspath, options.path)
    options.prefix = [p + os.path.sep for p in options.path]
    if options.all:
        options.at_level = sys.maxint

    if options.unit:
        options.layer = ['unit']
    if options.layer:
        options.layer = map(compile_filter, options.layer)

    options.layer = options.layer and dict([(l, 1) for l in options.layer])

    return options

# Command-line UI
###############################################################################

###############################################################################
# Install 2.4 TestSuite __iter__ into earlier versions

if sys.version_info < (2, 4):
    def __iter__(suite):
        return iter(suite._tests)
    unittest.TestSuite.__iter__ = __iter__
    del __iter__

# Install 2.4 TestSuite __iter__ into earlier versions
###############################################################################

###############################################################################
# Test the testrunner

def test_suite():

    return unittest.TestSuite() # XXX defeat autotest when in Five.

    import renormalizing
    checker = renormalizing.RENormalizing([
        (re.compile('^> [^\n]+->None$', re.M), '> ...->None'),
        (re.compile('\\\\'), '/'),   # hopefully, we'll make windows happy
        (re.compile('/r'), '\\\\r'), # undo damage from previous
        (re.compile(r'\r'), '\\\\r\n'),
        (re.compile(r'\d+[.]\d\d\d seconds'), 'N.NNN seconds'),
        (re.compile(r'\d+[.]\d\d\d ms'), 'N.NNN ms'),
        (re.compile('( |")[^\n]+testrunner-ex'), r'\1testrunner-ex'),
        (re.compile('( |")[^\n]+testrunner.py'), r'\1testrunner.py'),
        (re.compile(r'> [^\n]*(doc|unit)test[.]py\(\d+\)'),
                       r'\1doctest.py(NNN)'),
        (re.compile(r'[.]py\(\d+\)'), r'.py(NNN)'),
        (re.compile(r'[.]py:\d+'), r'.py:NNN'),
        (re.compile(r' line \d+,', re.IGNORECASE), r' Line NNN,'),

        # omit traceback entries for unittest.py or doctest.py from
        # output:
        (re.compile(r'^ +File "[^\n]+(doc|unit)test.py", [^\n]+\n[^\n]+\n',
                    re.MULTILINE),
         r''),
        (re.compile('^> [^\n]+->None$', re.M), '> ...->None'),
        (re.compile('import pdb; pdb'), 'Pdb()'), # Py 2.3

        ])

    def setUp(test):
        test.globs['saved-sys-info'] = sys.path, sys.argv
        test.globs['this_directory'] = os.path.split(__file__)[0]
        test.globs['testrunner_script'] = __file__

    def tearDown(test):
        sys.path, sys.argv = test.globs['saved-sys-info']

    suite = doctest.DocFileSuite(
        'testrunner.txt', 'testrunner-edge-cases.txt',
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS+doctest.NORMALIZE_WHITESPACE,
        checker=checker)

    if not __debug__:
        suite = unittest.TestSuite([suite, doctest.DocFileSuite(
            'profiling.txt',
            setUp=setUp, tearDown=tearDown,
            optionflags=doctest.ELLIPSIS+doctest.NORMALIZE_WHITESPACE,
            checker=checker)])

    return suite

def main():
    default = [
        '--path', os.path.split(sys.argv[0])[0],
        '--tests-pattern', '^testrunner$',
        ]
    run(default)

if __name__ == '__main__':

    # if --resume_layer is in the arguments, we are being run from the
    # test runner's own tests.  We need to adjust the path in hopes of
    # not getting a different version installed in the system python.
    if len(sys.argv) > 1 and sys.argv[1] == '--resume-layer':
        sys.path.insert(0,
            os.path.split(
                os.path.split(
                    os.path.split(
                        os.path.abspath(sys.argv[0])
                        )[0]
                    )[0]
                )[0]
            )

    # Hm, when run as a script, we need to import the testrunner under
    # it's own name, so that there's the imported flavor has the right
    # real_pdb_set_trace.
    try:
        import Products.Five.testing.testrunner
    except ImportError:
        pass
    else:
        from Products.Five.testing import doctest
        main()

# Test the testrunner
###############################################################################


# Delay import to give main an opportunity to fix up the path if
# necessary
try:
    from Products.Five.testing import doctest
except ImportError:
    import doctest
