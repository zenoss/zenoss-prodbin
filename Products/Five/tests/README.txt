Five tests
==========

All you have to do is type::

  $ bin/zopectl test --dir Products/Five

to run the Five tests.  You can also use the new test runner from Zope
2.9/Zope3.2 which has been added to just this version of Five::

  $ bin/zopectl run Products/Five/runtests.py -v -s Products.Five
