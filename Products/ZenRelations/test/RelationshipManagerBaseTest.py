#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipManagerBaseTest

Base class for RelationshipManager tests.  Sets up
a fake zope environement in which we can run our tests

$Id: RelationshipManagerBaseTest.py,v 1.3 2002/06/03 11:47:30 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import os, sys, unittest

import string, cStringIO, re
import ZODB, Acquisition
from OFS.Application import Application
from OFS.Folder import manage_addFolder
from OFS.Image import manage_addFile
from Testing.makerequest import makerequest
from webdav.common import rfc1123_date
from AccessControl import SecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from mimetools import Message
from multifile import MultiFile

class UnitTestSecurityPolicy:
    """
        Stub out the existing security policy for unit testing purposes.
    """
    #
    #   Standard SecurityPolicy interface
    #
    def validate( self
                , accessed=None
                , container=None
                , name=None
                , value=None
                , context=None
                , roles=None
                , *args
                , **kw):
        return 1
    
    def checkPermission( self, permission, object, context) :
        return 1

class UnitTestUser( Acquisition.Implicit ):
    """
        Stubbed out manager for unit testing purposes.
    """
    def getId( self ):
        return 'unit_tester'
    
    getUserName = getId

    def allowed( self, object, object_roles=None ):
        return 1

def makeConnection():
    import ZODB
    from ZODB.DemoStorage import DemoStorage

    s = DemoStorage(quota=(1<<20))
    return ZODB.DB( s ).open()

class RelationshipManagerBaseTest( unittest.TestCase ):
 
    def setUp( self ):
        self.connection = makeConnection()
        try:
            r = self.connection.root()
            a = Application()
            r['Application'] = a
            self.root = a
            a.id = 'Zope' #need this for ownership stuff
            responseOut = self.responseOut = cStringIO.StringIO()
            self.app = makerequest( self.root, stdout=responseOut )
        except:
            self.connection.close()
            raise
 
    def setUpSecurity(self):
        self.policy = UnitTestSecurityPolicy()
        self.oldPolicy = SecurityManager.setSecurityPolicy( self.policy )
        newSecurityManager( None, UnitTestUser().__of__( self.root ) )


    def tearDown( self ):
        get_transaction().abort()
        self.connection.close()
        del self.app
        del self.responseOut
        del self.root
        del self.connection
  

    def tearDownSecurity(self):
        noSecurityManager()
        SecurityManager.setSecurityPolicy( self.oldPolicy )
        del self.oldPolicy
        del self.policy
