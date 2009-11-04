load('env.rhino.js');
load('ext-base-debug.js');
load('ext-all-debug.js');
load('qunit.js');

var exit_status = 1;
var results = [];

QUnit.moduleStart = function(name, testEnvironment) {
    results.push('');
    results.push('  Starting module: ' + name);
};

QUnit.testStart = function(name) {
    results.push('    Starting test: ' + name);
};

QUnit.log = function(result, message) {
    results.push('      Assertion: ' + message + ' Success: ' + result);
};

QUnit.testDone = function(name, failures, total) {
    results.push('    Finished test: failures: ' + failures + ' / total: ' + total);
};

QUnit.moduleDone = function(name, failures, total) {
    results.push('  Finished module: failures: ' + failures + ' / total: ' + total);
};

QUnit.done = function(failures, total) {
    results.push('');
    results.push('Finished suite: failures: ' + failures + ' / total: ' + total);
    results.push('');
    exit_status = failures;
};
