#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""MasterTest

Load and run all RelationshipManager Test Cases

$Id: MasterTest.py,v 1.4 2003/10/21 17:32:26 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

import unittest
from ToManyRelationshipTest import ToManyRelationshipTest
from ToManyRelationshipTest2 import ToManyRelationshipTest2
from ToOneRelationshipTest import ToOneRelationshipTest
from SchemaManagerTest import SchemaManagerTest
from RelationshipSchemaTest import RelationshipSchemaTest
from RelationshipSchemaTest2 import RelationshipSchemaTest2
from RelationshipManagerTest import RelationshipManagerTest 

tests = (
        SchemaManagerTest,
        RelationshipSchemaTest,
        RelationshipSchemaTest2,
        ToOneRelationshipTest,
        ToManyRelationshipTest, 
        ToManyRelationshipTest2,
        RelationshipManagerTest,
       )

for t in tests:
    print "\nRunning test suite", t.__name__
    suite = unittest.makeSuite(t)
    unittest.TextTestRunner().run(suite)

