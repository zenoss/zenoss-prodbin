##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
# 
##############################################################################
""" Portal class

$Id: ZentinelPortal.py,v 1.17 2004/04/08 15:35:25 edahl Exp $
"""
 
import Globals
from Products.CMFCore.PortalObject import PortalObjectBase
from Products.CMFCore import PortalFolder
from Products.CMFCore.TypesTool import ContentFactoryMetadata
from Products.CMFCore.utils import getToolByName

import Company, DeviceGroup, Location, Rack
import Product, Hardware, Software
import Device, Server, Router, UBRRouter, TerminalServer
import System, Monitor, CricketConf, StatusMonitorConf
import DataRoot, DeviceClass, Classification
import IpNetwork, IpServiceClass, SystemClass

from Products.Confmon import getFactoryTypeInformation


class ZentinelPortal ( PortalObjectBase ):
    """
    The *only* function this class should have is to help in the setup
    of a new ZentinelPortal. It should not assist in the functionality at all.
    """
    meta_type = 'ZentinelPortal'

    _properties = (
        {'id':'title', 'type':'string'},
        {'id':'description', 'type':'text'},
        )
    title = ''
    description = ''

    def __init__( self, id, title='' ):
        PortalObjectBase.__init__( self, id, title )



Globals.InitializeClass(ZentinelPortal)


class PortalGenerator:

    klass = ZentinelPortal

    def setupTools(self, p):
        """Set up initial tools"""

        addCMFCoreTool = p.manage_addProduct['CMFCore'].manage_addTool
        addCMFCoreTool('CMF Actions Tool', None)
        addCMFCoreTool('CMF Member Data Tool', None)
        addCMFCoreTool('CMF Skins Tool', None)
        addCMFCoreTool('CMF Types Tool', None)


    def setupMailHost(self, p):
        p.manage_addProduct['MailHost'].manage_addMailHost(
            'MailHost', smtp_host='localhost')

    def setupUserFolder(self, p):
        p.manage_addProduct['OFSP'].manage_addUserFolder()

    def setupCookieAuth(self, p):
        p.manage_addProduct['CMFCore'].manage_addCC(
            id='cookie_authentication')

    def setupRoles(self, p):
        # Set up the suggested roles.
        p.getPhysicalRoot().__ac_roles__ += ('OneViewUser', 'OneViewMonitor',)

    def setupPermissions(self, p):
        # Set up some suggested role to permission mappings.
        mp = p.manage_permission

        mp('Set own password',['OneViewUser', 'OneViewMonitor', 'Manager',])
        mp('Set own properties',['OneViewUser','OneViewMonitor','Manager',])
        mp('List undoable changes',['OneViewUser','OneViewMonitor','Manager',])
        
        mp('View',['OneViewUser','OneViewMonitor','Manager',])
        mp('Manage Device Status',['OneViewMonitor','Manager',])
        
        # Add some other permissions mappings that may be helpful.
        mp('Delete objects',          ['Owner','Manager',],     1)
        mp('FTP access',              ['Owner','Manager',],     1)
        mp('Manage properties',       ['Owner','Manager',],     1)
        mp('Undo changes',            ['Owner','Manager',],     1)
        mp('View management screens', ['Owner','Manager',],     1)


    def setupDefaultSkins(self, p):
        from Products.CMFCore.DirectoryView import addDirectoryViews
        ps = getToolByName(p, 'portal_skins')
        addDirectoryViews(ps, 'skins', globals())
        ps.manage_addProduct['OFSP'].manage_addFolder(id='custom')
        ps.addSkinSelection('Basic',
            'custom, devices, organizers, misc, images', 
            make_default=1)
        p.setupCurrentSkin()


    def setupTypes(self, p, initial_types):
        tool = getToolByName(p, 'portal_types', None)
        if tool is None:
            return
        for t in initial_types:
            cfm = apply(ContentFactoryMetadata, (), t)
            tool._setObject(t['id'], cfm)
       

    def setupMimetypes(self, p):
        p.manage_addProduct[ 'CMFCore' ].manage_addRegistry()
        reg = p.content_type_registry

        reg.addPredicate( 'link', 'extension' )
        reg.getPredicate( 'link' ).edit( extensions="url, link" )
        reg.assignTypeName( 'link', 'Link' )

        reg.addPredicate( 'news', 'extension' )
        reg.getPredicate( 'news' ).edit( extensions="news" )
        reg.assignTypeName( 'news', 'News Item' )

        reg.addPredicate( 'document', 'major_minor' )
        reg.getPredicate( 'document' ).edit( major="text", minor="" )
        reg.assignTypeName( 'document', 'Document' )

        reg.addPredicate( 'image', 'major_minor' )
        reg.getPredicate( 'image' ).edit( major="image", minor="" )
        reg.assignTypeName( 'image', 'Image' )

        reg.addPredicate( 'file', 'major_minor' )
        reg.getPredicate( 'file' ).edit( major="application", minor="" )
        reg.assignTypeName( 'file', 'File' )


    def setup(self, p, create_userfolder):
        self.setupTools(p)
        self.setupMailHost(p)
        self.setupRoles(p)
        self.setupPermissions(p)
        self.setupDefaultSkins(p)
        self.setupTypes(p, getFactoryTypeInformation() )

    def create(self, parent, id, create_userfolder):
        id = str(id)
        portal = self.klass(id=id)
        parent._setObject(id, portal)
        # Return the fully wrapped object.
        p = parent.this()._getOb(id)
        self.setup(p, create_userfolder)
        return p

    def setupDefaultProperties(self, p, title, description,
                               email_from_address, email_from_name,
                               validate_email,
                               ):
        p._setProperty('email_from_address', email_from_address, 'string')
        p._setProperty('email_from_name', email_from_name, 'string')
        p._setProperty('validate_email', validate_email and 1 or 0, 'boolean')
        p.title = title
        p.description = description


manage_addZentinelPortal = Globals.HTMLFile('dtml/addPortal', globals())
manage_addZentinelPortal.__name__ = 'addPortal'

def manage_addZentinelPortal(self, id, title='Zentinel Portal', description='',
                         create_userfolder=0,
                         email_from_address='postmaster@localhost',
                         email_from_name='Portal Administrator',
                         validate_email=0, RESPONSE=None):
    '''
    Adds a portal instance.
    '''
    gen = PortalGenerator()
    from string import strip
    id = strip(id)
    p = gen.create(self, id, create_userfolder)
    gen.setupDefaultProperties(p, title, description,
                               email_from_address, email_from_name,
                               validate_email)
    if RESPONSE is not None:
        RESPONSE.redirect(self.absolute_url()+'/manage_main') 
