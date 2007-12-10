Products.Five.testing README
============================

Overview
--------

This package is lifted from the not-yet-in-Zope3 package located at:
svn+ssh://svn.zope.org/repos/main/zope.testing/trunk, as of 2005/09/25.
We are including it for the "goldegg-support" release of Five (perhaps
named "1.2"), in order to take advantage of its improved support for
debugging doctests (compared to that provided by the stock zope.testing
in Zope 2.8.1/3.0.1).


Nota Bene
---------

This package will be removed from Five as of version 1.3, at which
point the new 'zope.testing' code should be available in the Zope 2.9
/ Zope 3.2 tree.  Please do not add unnecessary dependencies, beyond
using the testrunner as described below.


Using the Package
-----------------

Assuming that your Zope instance home is '/var/zope/fivetest', and that
you have installed this version of Five into '$INSTANCE_HOME/Products',
create a script, e.g. '$INSTANCE_HOME/bin/newtest.py', with text as follows::

  
  #!/path/to/python
  import os, sys

  instance = os.path.abspath(os.path.join(os.path.split(sys.argv[0])[0], '..'))

  from Products.Five.testing import testrunner

  defaults = [
      '--path', instance,
      '--path', '%s/lib/python' % instance,
      '--package', 'Products',
      '--tests-pattern', '^tests$',
      ]

  sys.exit(testrunner.run(defaults))

You can then run tests within the instance home products.  To see all
available options::

  $ bin/zopectl run bin/newtest.py --help

To run all product tests, with dots::

  $ bin/zopectl run bin/newtest.py -v

 To run the tests for one product, showing the names of the tests::

  $ bin/zopectl run bin/newtest.py -vv Five

To run only the tests from one module, with timings::

  $ bin/zopectl run bin/newtest.py -vv Products.Five.tests.test_security

