##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Basic Site content type registry

$Id: ContentTypeRegistry.py 36457 2004-08-12 15:07:44Z jens $
"""

import re, os, urllib

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Globals import PersistentMapping
from OFS.SimpleItem import SimpleItem
from ZPublisher.mapply import mapply

from interfaces.ContentTypeRegistry \
        import ContentTypeRegistry as IContentTypeRegistry
from interfaces.ContentTypeRegistry \
        import ContentTypeRegistryPredicate as IContentTypeRegistryPredicate
from permissions import ManagePortal
from utils import _dtmldir
from utils import getToolByName


class MajorMinorPredicate( SimpleItem ):
    """
        Predicate matching on 'major/minor' content types.
        Empty major or minor implies wildcard (all match).
    """

    __implements__ = IContentTypeRegistryPredicate

    major = minor = None
    PREDICATE_TYPE  = 'major_minor'

    security = ClassSecurityInfo()

    def __init__( self, id ):
        self.id = id

    security.declareProtected( ManagePortal, 'getMajorType' )
    def getMajorType(self):
        """ Get major content types.
        """
        if self.major is None:
            return 'None'
        return ' '.join(self.major)

    security.declareProtected( ManagePortal, 'getMinorType' )
    def getMinorType(self):
        """ Get minor content types.
        """
        if self.minor is None:
            return 'None'
        return ' '.join(self.minor)

    security.declareProtected( ManagePortal, 'edit' )
    def edit( self, major, minor, COMMA_SPLIT=re.compile( r'[, ]' ) ):

        if major == 'None':
            major = None
        if type( major ) is type( '' ):
            major = filter( None, COMMA_SPLIT.split( major ) )

        if minor == 'None':
            minor = None
        if type( minor ) is type( '' ):
            minor = filter( None, COMMA_SPLIT.split( minor ) )

        self.major = major
        self.minor = minor

    #
    #   ContentTypeRegistryPredicate interface
    #
    security.declareObjectPublic()
    def __call__( self, name, typ, body ):
        """
            Return true if the rule matches, else false.
        """
        if self.major is None:
            return 0

        if self.minor is None:
            return 0

        typ = typ or '/'
        if not '/' in typ:
            typ = typ + '/'
        major, minor = typ.split('/', 1)

        if self.major and not major in self.major:
            return 0

        if self.minor and not minor in self.minor:
            return 0

        return 1

    security.declareProtected( ManagePortal, 'getTypeLabel' )
    def getTypeLabel( self ):
        """
            Return a human-readable label for the predicate type.
        """
        return self.PREDICATE_TYPE

    security.declareProtected( ManagePortal, 'predicateWidget' )
    predicateWidget = DTMLFile( 'majorMinorWidget', _dtmldir )

InitializeClass( MajorMinorPredicate )

class ExtensionPredicate( SimpleItem ):
    """
        Predicate matching on filename extensions.
    """

    __implements__ = IContentTypeRegistryPredicate

    extensions = None
    PREDICATE_TYPE  = 'extension'

    security = ClassSecurityInfo()

    def __init__( self, id ):
        self.id = id

    security.declareProtected( ManagePortal, 'getExtensions' )
    def getExtensions(self):
        """ Get filename extensions.
        """
        if self.extensions is None:
            return 'None'
        return ' '.join(self.extensions)

    security.declareProtected( ManagePortal, 'edit' )
    def edit( self, extensions, COMMA_SPLIT=re.compile( r'[, ]' ) ):

        if extensions == 'None':
            extensions = None
        if type( extensions ) is type( '' ):
            extensions = filter( None, COMMA_SPLIT.split( extensions ) )

        self.extensions = extensions

    #
    #   ContentTypeRegistryPredicate interface
    #
    security.declareObjectPublic()
    def __call__( self, name, typ, body ):
        """
            Return true if the rule matches, else false.
        """
        if self.extensions is None:
            return 0

        base, ext = os.path.splitext( name )
        if ext and ext[ 0 ] == '.':
            ext = ext[ 1: ]

        return ext in self.extensions

    security.declareProtected( ManagePortal, 'getTypeLabel' )
    def getTypeLabel( self ):
        """
            Return a human-readable label for the predicate type.
        """
        return self.PREDICATE_TYPE

    security.declareProtected( ManagePortal, 'predicateWidget' )
    predicateWidget = DTMLFile( 'extensionWidget', _dtmldir )

InitializeClass( ExtensionPredicate )

class MimeTypeRegexPredicate( SimpleItem ):
    """
        Predicate matching only on 'typ', using regex matching for
        string patterns (other objects conforming to 'match' can
        also be passed).
    """

    __implements__ = IContentTypeRegistryPredicate

    pattern         = None
    PREDICATE_TYPE  = 'mimetype_regex'

    security = ClassSecurityInfo()

    def __init__( self, id ):
        self.id = id

    security.declareProtected( ManagePortal, 'getPatternStr' )
    def getPatternStr( self ):
        if self.pattern is None:
            return 'None'
        return self.pattern.pattern

    security.declareProtected( ManagePortal, 'edit' )
    def edit( self, pattern ):
        if pattern == 'None':
            pattern = None
        if type( pattern ) is type( '' ):
            pattern = re.compile( pattern )
        self.pattern = pattern

    #
    #   ContentTypeRegistryPredicate interface
    #
    security.declareObjectPublic()
    def __call__( self, name, typ, body ):
        """
            Return true if the rule matches, else false.
        """
        if self.pattern is None:
            return 0

        return self.pattern.match( typ )

    security.declareProtected( ManagePortal, 'getTypeLabel' )
    def getTypeLabel( self ):
        """
            Return a human-readable label for the predicate type.
        """
        return self.PREDICATE_TYPE

    security.declareProtected( ManagePortal, 'predicateWidget' )
    predicateWidget = DTMLFile( 'patternWidget', _dtmldir )

InitializeClass( MimeTypeRegexPredicate )

class NameRegexPredicate( SimpleItem ):
    """
        Predicate matching only on 'name', using regex matching
        for string patterns (other objects conforming to 'match'
        and 'pattern' can also be passed).
    """

    __implements__ = IContentTypeRegistryPredicate

    pattern         = None
    PREDICATE_TYPE  = 'name_regex'

    security = ClassSecurityInfo()

    def __init__( self, id ):
        self.id = id

    security.declareProtected( ManagePortal, 'getPatternStr' )
    def getPatternStr( self ):
        """
            Return a string representation of our pattern.
        """
        if self.pattern is None:
            return 'None'
        return self.pattern.pattern

    security.declareProtected( ManagePortal, 'edit' )
    def edit( self, pattern ):
        if pattern == 'None':
            pattern = None
        if type( pattern ) is type( '' ):
            pattern = re.compile( pattern )
        self.pattern = pattern

    #
    #   ContentTypeRegistryPredicate interface
    #
    security.declareObjectPublic()
    def __call__( self, name, typ, body ):
        """
            Return true if the rule matches, else false.
        """
        if self.pattern is None:
            return 0

        return self.pattern.match( name )

    security.declareProtected( ManagePortal, 'getTypeLabel' )
    def getTypeLabel( self ):
        """
            Return a human-readable label for the predicate type.
        """
        return self.PREDICATE_TYPE

    security.declareProtected( ManagePortal, 'predicateWidget' )
    predicateWidget = DTMLFile( 'patternWidget', _dtmldir )

InitializeClass( NameRegexPredicate )


_predicate_types = []

def registerPredicateType( typeID, klass ):
    """
        Add a new predicate type.
    """
    _predicate_types.append( ( typeID, klass ) )

for klass in ( MajorMinorPredicate
             , ExtensionPredicate
             , MimeTypeRegexPredicate
             , NameRegexPredicate
             ):
    registerPredicateType( klass.PREDICATE_TYPE, klass )


class ContentTypeRegistry( SimpleItem ):
    """
        Registry for rules which map PUT args to a CMF Type Object.
    """

    __implements__ = IContentTypeRegistry

    meta_type = 'Content Type Registry'
    id = 'content_type_registry'

    manage_options = ( { 'label'    : 'Predicates'
                       , 'action'   : 'manage_predicates'
                       }
                     , { 'label'    : 'Test'
                       , 'action'   : 'manage_testRegistry'
                       }
                     ) + SimpleItem.manage_options

    security = ClassSecurityInfo()

    def __init__( self ):
        self.predicate_ids  = ()
        self.predicates     = PersistentMapping()

    #
    #   ZMI
    #
    security.declarePublic( 'listPredicateTypes' )
    def listPredicateTypes( self ):
        """
        """
        return map( lambda x: x[0], _predicate_types )

    security.declareProtected( ManagePortal, 'manage_predicates' )
    manage_predicates = DTMLFile( 'registryPredList', _dtmldir )

    security.declareProtected( ManagePortal, 'doAddPredicate' )
    def doAddPredicate( self, predicate_id, predicate_type, REQUEST ):
        """
        """
        self.addPredicate( predicate_id, predicate_type )
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_predicates'
                              + '?manage_tabs_message=Predicate+added.'
                              )

    security.declareProtected( ManagePortal, 'doUpdatePredicate' )
    def doUpdatePredicate( self
                         , predicate_id
                         , predicate
                         , typeObjectName
                         , REQUEST
                         ):
        """
        """
        self.updatePredicate( predicate_id, predicate, typeObjectName )
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_predicates'
                              + '?manage_tabs_message=Predicate+updated.'
                              )

    security.declareProtected( ManagePortal, 'doMovePredicateUp' )
    def doMovePredicateUp( self, predicate_id, REQUEST ):
        """
        """
        predicate_ids = list( self.predicate_ids )
        ndx = predicate_ids.index( predicate_id )
        if ndx == 0:
            msg = "Predicate+already+first."
        else:
            self.reorderPredicate( predicate_id, ndx - 1 )
            msg = "Predicate+moved."
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_predicates'
                              + '?manage_tabs_message=%s' % msg
                              )

    security.declareProtected( ManagePortal, 'doMovePredicateDown' )
    def doMovePredicateDown( self, predicate_id, REQUEST ):
        """
        """
        predicate_ids = list( self.predicate_ids )
        ndx = predicate_ids.index( predicate_id )
        if ndx == len( predicate_ids ) - 1:
            msg = "Predicate+already+last."
        else:
            self.reorderPredicate( predicate_id, ndx + 1 )
            msg = "Predicate+moved."
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_predicates'
                              + '?manage_tabs_message=%s' % msg
                              )

    security.declareProtected( ManagePortal, 'doRemovePredicate' )
    def doRemovePredicate( self, predicate_id, REQUEST ):
        """
        """
        self.removePredicate( predicate_id )
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_predicates'
                              + '?manage_tabs_message=Predicate+removed.'
                              )

    security.declareProtected( ManagePortal, 'manage_testRegistry' )
    manage_testRegistry = DTMLFile( 'registryTest', _dtmldir )

    security.declareProtected( ManagePortal, 'doTestRegistry' )
    def doTestRegistry( self, name, content_type, body, REQUEST ):
        """
        """
        typeName = self.findTypeName( name, content_type, body )
        if typeName is None:
            typeName = '<unknown>'
        else:
            types_tool = getToolByName(self, 'portal_types')
            typeName = types_tool.getTypeInfo(typeName).Title()
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                               + '/manage_testRegistry'
                               + '?testResults=Type:+%s'
                                       % urllib.quote( typeName )
                               )

    #
    #   Predicate manipulation
    #
    security.declarePublic( 'getPredicate' )
    def getPredicate( self, predicate_id ):
        """
            Find the predicate whose id is 'id';  return the predicate
            object, if found, or else None.
        """
        return self.predicates.get( predicate_id, ( None, None ) )[0]

    security.declarePublic( 'listPredicates' )
    def listPredicates( self ):
        """
            Return a sequence of tuples,
            '( id, ( predicate, typeObjectName ) )'
            for all predicates in the registry
        """
        result = []
        for predicate_id in self.predicate_ids:
            result.append( ( predicate_id, self.predicates[ predicate_id ] ) )
        return tuple( result )

    security.declarePublic( 'getTypeObjectName' )
    def getTypeObjectName( self, predicate_id ):
        """
            Find the predicate whose id is 'id';  return the name of
            the type object, if found, or else None.
        """
        return self.predicates.get( predicate_id, ( None, None ) )[1]

    security.declareProtected( ManagePortal, 'addPredicate' )
    def addPredicate( self, predicate_id, predicate_type ):
        """
            Add a predicate to this element of type 'typ' to the registry.
        """
        if predicate_id in self.predicate_ids:
            raise ValueError, "Existing predicate: %s" % predicate_id

        klass = None
        for key, value in _predicate_types:
            if key == predicate_type:
                klass = value

        if klass is None:
            raise ValueError, "Unknown predicate type: %s" % predicate_type

        self.predicates[ predicate_id ] = ( klass( predicate_id ), None )
        self.predicate_ids = self.predicate_ids + ( predicate_id, )

    security.declareProtected( ManagePortal, 'updatePredicate' )
    def updatePredicate( self, predicate_id, predicate, typeObjectName ):
        """
            Update a predicate in this element.
        """
        if not predicate_id in self.predicate_ids:
            raise ValueError, "Unknown predicate: %s" % predicate_id

        predObj = self.predicates[ predicate_id ][0]
        mapply( predObj.edit, (), predicate.__dict__ )
        self.assignTypeName( predicate_id, typeObjectName )

    security.declareProtected( ManagePortal, 'removePredicate' )
    def removePredicate( self, predicate_id ):
        """
            Remove a predicate from the registry.
        """
        del self.predicates[ predicate_id ]
        idlist = list( self.predicate_ids )
        ndx = idlist.index( predicate_id )
        idlist = idlist[ :ndx ] + idlist[ ndx+1: ]
        self.predicate_ids = tuple( idlist )

    security.declareProtected( ManagePortal, 'reorderPredicate' )
    def reorderPredicate( self, predicate_id, newIndex ):
        """
            Move a given predicate to a new location in the list.
        """
        idlist = list( self.predicate_ids )
        ndx = idlist.index( predicate_id )
        pred = idlist[ ndx ]
        idlist = idlist[ :ndx ] + idlist[ ndx+1: ]
        idlist.insert( newIndex, pred )
        self.predicate_ids = tuple( idlist )

    security.declareProtected( ManagePortal, 'assignTypeName' )
    def assignTypeName( self, predicate_id, typeObjectName ):
        """
            Bind the given predicate to a particular type object.
        """
        pred, oldTypeObjName = self.predicates[ predicate_id ]
        self.predicates[ predicate_id ] = ( pred, typeObjectName )

    #
    #   ContentTypeRegistry interface
    #
    def findTypeName( self, name, typ, body ):
        """
            Perform a lookup over a collection of rules, returning the
            the name of the Type object corresponding to name/typ/body.
            Return None if no match found.
        """
        for predicate_id in self.predicate_ids:
            pred, typeObjectName = self.predicates[ predicate_id ]
            if pred( name, typ, body ):
                return typeObjectName

        return None

InitializeClass( ContentTypeRegistry )

def manage_addRegistry( self, REQUEST=None ):
    """
        Add a CTR to self.
    """
    CTRID = ContentTypeRegistry.id
    reg = ContentTypeRegistry()
    self._setObject( CTRID, reg )
    reg = self._getOb( CTRID )

    if REQUEST is not None:
        REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                              + '/manage_main'
                              + '?manage_tabs_message=Registry+added.'
                              )
