###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import os.path
import logging

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.zenmib import ZenMib, MibFile, PackageManager

class FakeConfigs: pass

class FakeOptions:
    def __init__(self):
        self.nocommit = True


class Testzenmib(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)

        # Trap n toss all output to make the test prettier
        # Otherwise it will drive you insane, yelling
        # "SHUT UP! SHUT UP!" to your monitor.
        # Since no good will come of that...
        logging.disable(logging.INFO)
        logging.disable(logging.WARN)
        logging.disable(logging.ERROR)
        logging.disable(logging.CRITICAL)

        # Note: the docs (http://docs.python.org/library/logging.html#logging-levels)
        #       imply that we can override the above behaviour by passing
        #       a handler object to logging.getLogger().addHandler(handler),
        #       but that doesn't seem to work.

        self.zmib = ZenMib(noopts=1)
        self.zmib.options = FakeOptions()

        self.mfo = MibFile('filename', '')
        self.log = logging.getLogger("zen.ZenMib")


    def testFindDependencies(self):
        """
        Given a MIB, find out what it relies on
        """
        mib1 = """
RFC1213-MIB DEFINITIONS ::= BEGIN 

IMPORTS
       experimental, OBJECT-TYPE, Counter
            FROM RFC1155-SMI;

root    OBJECT IDENTIFIER ::= { experimental xx }

END
"""
        mfo = MibFile('filename', mib1)
        self.assert_('RFC1213-MIB' in mfo.mibs)
        depends = mfo.mibToDeps['RFC1213-MIB']
        self.assert_(len(depends) == 1)
        self.assert_('RFC1155-SMI' in depends)

        mib2 = """
RFC1213-MIB DEFINITIONS ::= BEGIN 

IMPORTS
  MODULE-IDENTITY, OBJECT-TYPE,  enterprises, Integer32,
  TimeTicks,NOTIFICATION-TYPE             FROM SNMPv2-SMI
  DisplayString                           FROM RFC1213-MIB
  MODULE-COMPLIANCE, OBJECT-GROUP,
  NOTIFICATION-GROUP                      FROM SNMPv2-CONF;

root    OBJECT IDENTIFIER ::= { experimental xx }

END
"""
        mfo = MibFile('filename', mib2)
        self.assert_('RFC1213-MIB' in mfo.mibs)
        depends = mfo.mibToDeps['RFC1213-MIB']
        self.assert_(len(depends) == 3)
        self.assertEquals(depends,
                  set(['SNMPv2-SMI', 'RFC1213-MIB', 'SNMPv2-CONF']))



    def XtestFilterOutNonAscii(self):
        """
        Currently, we don't support multi-byte language exports
        when ZenPacks are exported.  Control characters cause
        imports to freak out too.
        """
        pass  # Not implemented yet


    def testComments(self):
        """
        Ignore comments
        """
        mib = """
RFC1213-MIB DEFINITIONS ::= BEGIN 
aaa
--sss--
bbb --ttt
ccc --uuu-- ddd
eee --vvv--
"This is text" --www-- "This is ""quoted"" text"
"This is more quoted ""text"" " followed by file.
------------------------------------------
-- Lines with all dashes are not valid ASN.1 comments
-- We ignore them anyway
------------------------------------------
---- --This is an empty comment
Text with an ---- empty comment in the middle
--This is a comment with a "quote" -- But wait, here's text
And now more text -- Stupid "quoted" comment
Finally, the last -- "Quoted" comment

/* block comments present "more" of a problem
   because they can --contain other comments
   and event the " symbol that throws everything
   off. You can even --single line */ finish a 
   single line comment inside of a double quote

But what happens --if you insert /* a block
comment within */ a single line comment. There
is also the issue of a "block comment /* within
a */ string"

/*Oh, what about nested comments, almost
  /* forgot about nested comments
    /*they seem like they should cut out without*/
  */
*/
Just some more text here.

END
"""
        noComments = """
RFC1213-MIB DEFINITIONS ::= BEGIN 
aaa

bbb 
ccc  ddd
eee 
"This is text"  "This is ""quoted"" text"
"This is more quoted ""text"" " followed by file.




 
Text with an  empty comment in the middle
 But wait, here's text
And now more text 
Finally, the last 

 finish a 
   single line comment inside of a double quote

But what happens 
comment within */ a single line comment. There
is also the issue of a "block comment /* within
a */ string"


Just some more text here.

END
"""

        justMib = self.mfo.removeMibComments(mib)
        self.assertEquals(justMib, noComments)
        

    def testMIBSplits(self):
        """
        Can we split properly?
        """
        mib1 = """
IMPORT1 DEFINITIONS ::= BEGIN

    IMPORTS
        myroot      FROM NOIMPORT1;

    level  OBJECT IDENTIFIER ::= { myroot 1 }
END

"""
        mib2 = """
IMPORT1 DEFINITIONS ::= BEGIN

    IMPORTS
        myroot      FROM NOIMPORT1;

    level  OBJECT IDENTIFIER ::= { myroot 1 }
END

IMPORT2 DEFINITIONS ::= BEGIN

    IMPORTS
        level      FROM IMPORT1
        myroot      FROM NOIMPORT1;

    level2  OBJECT IDENTIFIER ::= { level1 1 }
    m2n64   OBJECT IDENTIFIER ::= { myroot 64 }

END
"""
        mibs = self.mfo.splitFileToMIBs(mib1)
        self.assertEquals(len(mibs), 1)

        mibs = self.mfo.splitFileToMIBs(mib2)
        self.assertEquals(len(mibs), 2)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenmib))
    return suite

