##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit tests for WorkflowTool module.

$Id: test_WorkflowTool.py 39511 2005-10-19 13:32:29Z tseaver $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from OFS.SimpleItem import SimpleItem

from Products.CMFCore.tests.base.testcase import WarningInterceptor


class Dummy( SimpleItem ):

    def __init__( self, id ):
        self._id = id

    def getId( self ):
        return self._id


class DummyWorkflow( Dummy ):

    meta_type = 'DummyWorkflow'
    _isAWorkflow = 1
    _known_actions=()
    _known_info=()

    def __init__( self, id ):
        Dummy.__init__( self, id )
        self._did_action = {}
        self._gave_info = {}
        self._notified = {}

    def setKnownActions( self, known_actions ):
        self._known_actions = known_actions

    def setKnownInfo( self, known_info ):
        self._known_info = known_info

    def didAction( self, action ):
        return self._did_action.setdefault( action, [] )

    def gaveInfo( self, name ):
        return self._gave_info.setdefault( name, [] )

    def notified( self, name ):
        return self._notified.setdefault( name, [] )

    #
    #   WorkflowDefinition interface
    #
    def getCatalogVariablesFor( self, ob ):
        return { 'dummy' : '%s: %s' % ( self.getId(), ob.getId() ) }

    def updateRoleMappingsFor( self, ob ):
        pass

    def listObjectActions( self, info ):
        return () #XXX

    def listGlobalActions( self, info ):
        return () #XXX

    def isActionSupported( self, ob, action ):
        return action in self._known_actions

    def doActionFor( self, ob, action, *args, **kw ):
        self.didAction( action ).append( ob )

    def isInfoSupported( self, ob, name ):
        return name in self._known_info

    def getInfoFor( self, ob, name, default, *args, **kw ):
        self.gaveInfo( name ).append( ob )
        return name in self._known_info and 1 or 0

    def notifyCreated( self, ob ):
        self.notified( 'created' ).append( ( ob, ) )

    def notifyBefore( self, ob, action ):
        self.notified( 'before' ).append( ( ob, action ) )

    def notifySuccess( self, ob, action, result ):
        self.notified( 'success' ).append( ( ob, action, result ) )

    def notifyException( self, ob, action, exc ):
        self.notified( 'exception' ).append( ( ob, action, exc ) )


class DummyContent( Dummy ):

    meta_type = 'Dummy'
    _isPortalContent = 1

    def getPortalTypeName(self):
        return 'Dummy Content'


class DummyNotReallyContent( Dummy ):

    meta_type = 'Dummy Content'


class DummyTypeInfo( Dummy ):

    pass


class DummyTypesTool( SimpleItem ):

    def listTypeInfo( self ):
        return [ DummyTypeInfo( 'Dummy Content' ) ]

    def getTypeInfo( self, ob ):
        if getattr( ob, 'meta_type', None ) is 'Dummy':
            return DummyTypeInfo( 'Dummy Content' )
        return None


class WorkflowToolTests(TestCase, WarningInterceptor):

    def setUp( self ):
        from Products.CMFCore.WorkflowTool import addWorkflowFactory
        addWorkflowFactory( DummyWorkflow )

    def tearDown( self ):
        from Products.CMFCore.WorkflowTool import _removeWorkflowFactory
        _removeWorkflowFactory( DummyWorkflow )
        self._free_warning_output()

    def _makeOne( self, workflow_ids=() ):
        from Products.CMFCore.WorkflowTool import WorkflowTool

        tool = WorkflowTool()

        for workflow_id in workflow_ids:
            tool.manage_addWorkflow( DummyWorkflow.meta_type, workflow_id )

        return tool

    def _makeRoot( self ):

        from OFS.Folder import Folder
        root = Folder( 'root' )
        tt = DummyTypesTool()
        root._setObject( 'portal_types', tt )
        return root

    def _makeWithTypes( self ):
        root = self._makeRoot()
        return self._makeOne( workflow_ids=( 'a', 'b' ) ).__of__( root )

    def _makeWithTypesAndChain( self ):

        tool = self._makeWithTypes()
        tool.setChainForPortalTypes( ( 'Dummy Content', ), ( 'a', 'b' ) )
        return tool

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.portal_actions \
                import ActionProvider as IActionProvider
        from Products.CMFCore.interfaces.portal_workflow \
                import portal_workflow as IWorkflowTool
        from Products.CMFCore.WorkflowTool import WorkflowTool

        verifyClass(IActionProvider, WorkflowTool)
        verifyClass(IWorkflowTool, WorkflowTool)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IActionProvider
            from Products.CMFCore.interfaces import IWorkflowTool
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.WorkflowTool import WorkflowTool

        verifyClass(IActionProvider, WorkflowTool)
        verifyClass(IWorkflowTool, WorkflowTool)

    def test_empty( self ):

        from Products.CMFCore.WorkflowTool import WorkflowException

        tool = self._makeOne()

        self.failIf( tool.getWorkflowIds() )
        self.assertEqual( tool.getWorkflowById( 'default_workflow' ), None )
        self.assertEqual( tool.getWorkflowById( 'a' ), None )

        self.assertRaises( WorkflowException, tool.getInfoFor, None, 'hmm' )
        self.assertRaises( WorkflowException, tool.doActionFor, None, 'hmm' )

    def test_new_with_wf( self ):

        from Products.CMFCore.WorkflowTool import WorkflowException

        tool = self._makeWithTypes()

        wfids = tool.getWorkflowIds()
        self.assertEqual( len( wfids ), 2 )
        self.failUnless( 'a' in wfids )
        self.failUnless( 'b' in wfids )
        self.assertEqual( tool.getWorkflowById( 'default' ), None )
        wf = tool.getWorkflowById( 'a' )
        self.assertEqual( wf.getId(), 'a' )
        wf = tool.getWorkflowById( 'b' )
        self.assertEqual( wf.getId(), 'b' )

        self.assertRaises( WorkflowException, tool.getInfoFor, None, 'hmm' )
        self.assertRaises( WorkflowException, tool.doActionFor, None, 'hmm' )

    def test_nonContent( self ):

        tool = self._makeWithTypesAndChain()
        self.assertEquals( len( tool.getDefaultChainFor( None ) ), 0 )
        self.assertEquals( len( tool.getChainFor( None ) ), 0 )
        self.assertEquals( len( tool.getCatalogVariablesFor( None ) ), 0 )

    def test_notReallyContent( self ):

        tool = self._makeWithTypesAndChain()
        dummy = DummyNotReallyContent( 'doh' )
        self.assertEquals( len( tool.getDefaultChainFor( dummy ) ), 0 )
        self.assertEquals( len( tool.getChainFor( dummy ) ), 0 )
        self.assertEquals( len( tool.getCatalogVariablesFor( dummy ) ), 0 )

    def test_content_default_chain( self ):

        tool = self._makeWithTypes()
        dummy = DummyContent( 'dummy' )
        self.assertEquals( len( tool.getDefaultChainFor( dummy ) ), 1 )
        self.assertEquals( len( tool.getChainFor( dummy ) ), 1 )
        self.assertEquals( len( tool.getCatalogVariablesFor( dummy ) ), 0 )
        self.assertEquals( tool.getDefaultChainFor( dummy )
                         , tool.getChainFor( dummy ) )

    def test_content_own_chain( self ):

        tool = self._makeWithTypesAndChain()

        dummy = DummyContent( 'dummy' )

        self.assertEquals( len( tool.getDefaultChainFor( dummy ) ), 1 )
        chain = tool.getChainFor( dummy )
        self.assertEquals( len( chain ), 2 )
        self.failUnless( 'a' in chain )
        self.failUnless( 'b' in chain )

        vars = tool.getCatalogVariablesFor( dummy )
        self.assertEquals( len( vars ), 1 )
        self.failUnless( 'dummy' in vars.keys() )
        self.failUnless( 'a: dummy' in vars.values() )

    def test_setChainForPortalTypes(self):

        tool = self._makeWithTypes()
        dummy = DummyContent('dummy')

        tool.setChainForPortalTypes( ('Dummy Content',), ('a', 'b') )
        self.assertEquals( tool.getChainFor(dummy), ('a', 'b') )
        tool.setChainForPortalTypes( ('Dummy Content',), 'a, b' )
        self.assertEquals( tool.getChainFor(dummy), ('a', 'b') )

        tool.setChainForPortalTypes( ('Dummy Content',), () )
        self.assertEquals( tool.getChainFor(dummy), () )
        tool.setChainForPortalTypes( ('Dummy Content',), '' )
        self.assertEquals( tool.getChainFor(dummy), () )

    def test_getCatalogVariablesFor( self ):

        tool = self._makeWithTypesAndChain()
        dummy = DummyContent( 'dummy' )

        vars = tool.getCatalogVariablesFor( dummy )
        self.assertEquals( len( vars ), 1 )
        self.failUnless( 'dummy' in vars.keys() )
        self.failUnless( 'a: dummy' in vars.values() )

    def test_getActionsFor( self ):

        import warnings

        # Collector #360: Test AtttributeError in deprecated API :(
        tool = self._makeWithTypesAndChain()
        dummy = DummyContent( 'dummy' )

        self._trap_warning_output()
        actions = tool.getActionsFor( dummy )
        self.assertEqual( len( actions ), 0 )

    def test_getInfoFor( self ):

        tool = self._makeWithTypesAndChain()
        tool.b.setKnownInfo( ( 'info', ) )
        dummy = DummyContent( 'dummy' )

        info = tool.getInfoFor( dummy, 'info' )

        self.assertEqual( info, 1 )
        self.failIf( tool.a.gaveInfo( 'info' ) )
        self.failUnless( tool.b.gaveInfo( 'info' ) )

    def test_doActionFor( self ):

        tool = self._makeWithTypesAndChain()
        tool.a.setKnownActions( ( 'action', ) )
        dummy = DummyContent( 'dummy' )

        tool.doActionFor( dummy, 'action' )

        self.failUnless( tool.a.didAction( 'action' ) )
        self.failIf( tool.b.didAction( 'action' ) )

    def test_notifyCreated( self ):

        tool = self._makeWithTypesAndChain()

        ob = DummyContent( 'dummy' )
        tool.notifyCreated( ob )

        for wf in tool.a, tool.b:
            notified = wf.notified( 'created' )
            self.assertEqual( len( notified ), 1 )
            self.assertEqual( notified[0], ( ob, ) )

    def test_notifyBefore( self ):

        tool = self._makeWithTypesAndChain()

        ob = DummyContent( 'dummy' )
        tool.notifyBefore( ob, 'action' )

        for wf in tool.a, tool.b:
            notified = wf.notified( 'before' )
            self.assertEqual( len( notified ), 1 )
            self.assertEqual( notified[0], ( ob, 'action' ) )

    def test_notifySuccess( self ):

        tool = self._makeWithTypesAndChain()

        ob = DummyContent( 'dummy' )
        tool.notifySuccess( ob, 'action' )

        for wf in tool.a, tool.b:
            notified = wf.notified( 'success' )
            self.assertEqual( len( notified ), 1 )
            self.assertEqual( notified[0], ( ob, 'action', None ) )

    def test_notifyException( self ):

        tool = self._makeWithTypesAndChain()

        ob = DummyContent( 'dummy' )
        tool.notifyException( ob, 'action', 'exception' )

        for wf in tool.a, tool.b:
            notified = wf.notified( 'exception' )
            self.assertEqual( len( notified ), 1 )
            self.assertEqual( notified[0], ( ob, 'action', 'exception' ) )

    def xxx_test_updateRoleMappings( self ):
        """
            Build a tree of objects, invoke tool.updateRoleMappings,
            and then check to see that the workflows each got called;
            check the resulting count, as well.
        """


def test_suite():
    return TestSuite((
        makeSuite(WorkflowToolTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
