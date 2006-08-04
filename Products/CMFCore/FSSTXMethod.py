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
""" FSSTXMethod: Filesystem methodish Structured Text document.

$Id: FSSTXMethod.py 37990 2005-08-18 16:43:36Z jens $
"""

import Globals
from AccessControl import ClassSecurityInfo
from StructuredText.StructuredText import HTML

from permissions import FTPAccess
from permissions import View
from permissions import ViewManagementScreens
from DirectoryView import registerFileExtension
from DirectoryView import registerMetaType
from FSObject import FSObject
from utils import _dtmldir
from utils import expandpath


class FSSTXMethod( FSObject ):
    """
        A chunk of StructuredText, rendered as a skin method of a
        CMFSite.
    """

    meta_type = 'Filesystem STX Method'

    manage_options=( { 'label'      : 'Customize'
                     , 'action'     : 'manage_main'
                     }
                   , { 'label'      : 'View'
                     , 'action'     : ''
                     , 'help'       : ('OFSP'
                                      ,'DTML-DocumentOrMethod_View.stx'
                                      )
                     }
                   )

    security = ClassSecurityInfo()
    security.declareObjectProtected( View )

    security.declareProtected( ViewManagementScreens, 'manage_main')
    manage_main = Globals.DTMLFile( 'custstx', _dtmldir )

    #
    #   FSObject interface
    #
    def _createZODBClone(self):
        """
            Create a ZODB (editable) equivalent of this object.
        """
        raise NotImplementedError, "See next week's model."

    def _readFile( self, reparse ):

        fp = expandpath( self._filepath )
        file = open( fp, 'r' )  # not binary, we want CRLF munging here.

        try:
            data = file.read()
        finally:
            file.close()

        self.raw = data

        if reparse:
            self.cook()

    #
    #   "Wesleyan" interface (we need to be "methodish").
    #
    class func_code:
        pass

    func_code=func_code()
    func_code.co_varnames= ()
    func_code.co_argcount=0
    func_code.__roles__=()

    func_defaults__roles__=()
    func_defaults=()

    index_html = None   # No accidental acquisition

    default_content_type = 'text/html'

    def cook( self ):
        if not hasattr( self, '_v_cooked' ):
            self._v_cooked = HTML(self.raw, level=1, header=0)
        return self._v_cooked

    _default_template = Globals.HTML( """\
<dtml-var standard_html_header>
<div class="Desktop">
<dtml-var cooked>
</div>
<dtml-var standard_html_footer>""" )

    def __call__( self, REQUEST={}, RESPONSE=None, **kw ):
        """
            Return our rendered StructuredText.
        """
        self._updateFromFS()

        if RESPONSE is not None:
            RESPONSE.setHeader( 'Content-Type', 'text/html' )
        return self._render(REQUEST, RESPONSE, **kw)

    security.declarePrivate( '_render' )
    def _render( self, REQUEST={}, RESPONSE=None, **kw ):
        """
            Find the appropriate rendering template and use it to
            render us.
        """
        template = getattr( self, 'stxmethod_view', self._default_template )

        if getattr( template, 'isDocTemp', 0 ):
            posargs = ( self, REQUEST, RESPONSE )
        else:
            posargs = ()

        return template(*posargs, **{ 'cooked' : self.cook() } )

    security.declareProtected( FTPAccess, 'manage_FTPget' )
    def manage_FTPget( self ):
        """
            Fetch our source for delivery via FTP.
        """
        return self.raw

    security.declareProtected( ViewManagementScreens, 'PrincipiaSearchSource' )
    def PrincipiaSearchSource( self ):
        """
            Fetch our source for indexing in a catalog.
        """
        return self.raw

    security.declareProtected( ViewManagementScreens, 'document_src' )
    def document_src( self ):
        """
            Fetch our source for indexing in a catalog.
        """
        return self.raw

Globals.InitializeClass( FSSTXMethod )

registerFileExtension( 'stx', FSSTXMethod )
registerMetaType( 'STX Method', FSSTXMethod )
