##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" GenericSetup:  Role-permission export / import

$Id: rolemap.py 41625 2006-02-15 11:39:43Z yuppie $
"""

from AccessControl import ClassSecurityInfo
from AccessControl.Permission import Permission
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from permissions import ManagePortal
from utils import _xmldir
from utils import ConfiguratorBase
from utils import CONVERTER, DEFAULT, KEY


#
#   Configurator entry points
#
_FILENAME = 'rolemap.xml'

def importRolemap( context ):

    """ Import roles / permission map from an XML file.

    o 'context' must implement IImportContext.

    o Register via Python:

      registry = site.setup_tool.setup_steps
      registry.registerStep( 'importRolemap'
                           , '20040518-01'
                           , Products.GenericSetup.rolemap.importRolemap
                           , ()
                           , 'Role / Permission import'
                           , 'Import additional roles, and map '
                           'roles to permissions'
                           )

    o Register via XML:

      <setup-step id="importRolemap"
                  version="20040518-01"
                  handler="Products.GenericSetup.rolemap.importRolemap"
                  title="Role / Permission import"
      >Import additional roles, and map roles to permissions.</setup-step>

    """
    site = context.getSite()
    encoding = context.getEncoding()
    logger = context.getLogger('rolemap')

    if context.shouldPurge():

        items = site.__dict__.items()

        for k, v in items: # XXX: WAAA

            if k == '__ac_roles__':
                delattr( site, k )

            if k.startswith( '_' ) and k.endswith( '_Permission' ):
                delattr( site, k )

    text = context.readDataFile( _FILENAME )

    if text is not None:

        rc = RolemapConfigurator( site, encoding )
        rolemap_info = rc.parseXML( text )

        immediate_roles = list( getattr(site, '__ac_roles__', []) )
        already = {}

        for role in site.valid_roles():
            already[ role ] = 1

        for role in rolemap_info[ 'roles' ]:

            if already.get( role ) is None:
                immediate_roles.append( role )
                already[ role ] = 1

        immediate_roles.sort()
        site.__ac_roles__ = tuple( immediate_roles )

        for permission in rolemap_info[ 'permissions' ]:

            site.manage_permission( permission[ 'name' ]
                                  , permission[ 'roles' ]
                                  , permission[ 'acquire' ]
                                  )

    logger.info('Role / permission map imported.')


def exportRolemap( context ):

    """ Export roles / permission map as an XML file

    o 'context' must implement IExportContext.

    o Register via Python:

      registry = site.setup_tool.export_steps
      registry.registerStep( 'exportRolemap'
                           , Products.GenericSetup.rolemap.exportRolemap
                           , 'Role / Permission export'
                           , 'Export additional roles, and '
                             'role / permission map '
                           )

    o Register via XML:

      <export-script id="exportRolemap"
                     version="20040518-01"
                     handler="Products.GenericSetup.rolemap.exportRolemap"
                     title="Role / Permission export"
      >Export additional roles, and role / permission map.</export-script>

    """
    site = context.getSite()
    logger = context.getLogger('rolemap')

    rc = RolemapConfigurator( site ).__of__( site )
    text = rc.generateXML()

    context.writeDataFile( _FILENAME, text, 'text/xml' )

    logger.info('Role / permission map exported.')


class RolemapConfigurator(ConfiguratorBase):
    """ Synthesize XML description of sitewide role-permission settings.
    """
    security = ClassSecurityInfo()

    security.declareProtected( ManagePortal, 'listRoles' )
    def listRoles( self ):

        """ List the valid role IDs for our site.
        """
        return self._site.valid_roles()

    security.declareProtected( ManagePortal, 'listPermissions' )
    def listPermissions( self ):

        """ List permissions for export.

        o Returns a sqeuence of mappings describing locally-modified
          permission / role settings.  Keys include:

          'permission' -- the name of the permission

          'acquire' -- a flag indicating whether to acquire roles from the
              site's container

          'roles' -- the list of roles which have the permission.

        o Do not include permissions which both acquire and which define
          no local changes to the acquired policy.
        """
        permissions = []
        valid_roles = self.listRoles()

        for perm in self._site.ac_inherited_permissions( 1 ):

            name = perm[ 0 ]
            p = Permission( name, perm[ 1 ], self._site )
            roles = p.getRoles( default=[] )
            acquire = isinstance( roles, list )  # tuple means don't acquire
            roles = [ r for r in roles if r in valid_roles ]
            roles.sort()

            if roles or not acquire:
                permissions.append( { 'name'    : name
                                    , 'acquire' : acquire
                                    , 'roles'   : roles
                                    } )

        return permissions

    def _getExportTemplate(self):

        return PageTemplateFile('rmeExport.xml', _xmldir)

    def _getImportMapping(self):

        return {
          'rolemap':
            { 'roles':       {CONVERTER: self._convertToUnique, DEFAULT: ()},
              'permissions': {CONVERTER: self._convertToUnique} },
          'roles':
            { 'role':        {KEY: None} },
          'role':
            { 'name':        {KEY: None} },
          'permissions':
            { 'permission':  {KEY: None, DEFAULT: ()} },
          'permission':
            { 'name':        {},
              'role':        {KEY: 'roles'},
              'acquire':     {CONVERTER: self._convertToBoolean} } }

InitializeClass(RolemapConfigurator)
