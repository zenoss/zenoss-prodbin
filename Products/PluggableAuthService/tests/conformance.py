##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Base classes for testing plugin interface conformance.

$Id: conformance.py 70769 2006-10-18 03:10:50Z jens $
"""

try:
    from zope.interface.verify import verifyClass
except ImportError:
    from Interface.Verify import verifyClass


class IExtractionPlugin_conformance:

    def test_IExtractionPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IExtractionPlugin

        verifyClass( IExtractionPlugin, self._getTargetClass() )

    def test_IExtractionPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IExtractionPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IExtractionPlugin.__name__ in listed)


class ILoginPasswordExtractionPlugin_conformance:

    def test_ILoginPasswordExtractionPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import ILoginPasswordExtractionPlugin

        verifyClass( ILoginPasswordExtractionPlugin, self._getTargetClass() )

    def test_ILoginPasswordExtractionPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import ILoginPasswordExtractionPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(ILoginPasswordExtractionPlugin.__name__ in listed)


class ILoginPasswordHostExtractionPlugin_conformance:

    def test_ILoginPasswordHostExtractionPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import ILoginPasswordHostExtractionPlugin

        verifyClass( ILoginPasswordHostExtractionPlugin
                   , self._getTargetClass() )

    def test_ILoginPasswordHostExtractionPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import ILoginPasswordHostExtractionPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(ILoginPasswordHostExtractionPlugin.__name__ in listed)


class IChallengePlugin_conformance:

    def test_IChallengePlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IChallengePlugin

        verifyClass( IChallengePlugin, self._getTargetClass() )

    def test_IChallengePlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IChallengePlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IChallengePlugin.__name__ in listed)


class ICredentialsUpdatePlugin_conformance:

    def test_ICredentialsUpdatePlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import ICredentialsUpdatePlugin

        verifyClass( ICredentialsUpdatePlugin, self._getTargetClass() )

    def test_ICredentialsUpdatePlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import ICredentialsUpdatePlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(ICredentialsUpdatePlugin.__name__ in listed)


class ICredentialsResetPlugin_conformance:

    def test_ICredentialsResetPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import ICredentialsResetPlugin

        verifyClass( ICredentialsResetPlugin, self._getTargetClass() )

    def test_ICredentialsResetPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import ICredentialsResetPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(ICredentialsResetPlugin.__name__ in listed)


class IAuthenticationPlugin_conformance:

    def test_AuthenticationPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IAuthenticationPlugin

        verifyClass( IAuthenticationPlugin, self._getTargetClass() )

    def test_IAuthenticationPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IAuthenticationPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IAuthenticationPlugin.__name__ in listed)


class IUserEnumerationPlugin_conformance:

    def test_UserEnumerationPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IUserEnumerationPlugin

        verifyClass( IUserEnumerationPlugin, self._getTargetClass() )

    def test_IUserEnumerationPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IUserEnumerationPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IUserEnumerationPlugin.__name__ in listed)


class IUserAdderPlugin_conformance:

    def test_UserAdderPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IUserAdderPlugin

        verifyClass( IUserAdderPlugin, self._getTargetClass() )

    def test_IUserAdderPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IUserAdderPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IUserAdderPlugin.__name__ in listed)


class IGroupEnumerationPlugin_conformance:

    def test_GroupEnumerationPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IGroupEnumerationPlugin

        verifyClass( IGroupEnumerationPlugin, self._getTargetClass() )

    def test_IGroupEnumerationPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IGroupEnumerationPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IGroupEnumerationPlugin.__name__ in listed)


class IGroupsPlugin_conformance:

    def test_GroupsPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IGroupsPlugin

        verifyClass( IGroupsPlugin, self._getTargetClass() )

    def test_IGroupsPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IGroupsPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IGroupsPlugin.__name__ in listed)


class IRoleEnumerationPlugin_conformance:

    def test_RoleEnumerationPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRoleEnumerationPlugin

        verifyClass( IRoleEnumerationPlugin, self._getTargetClass() )

    def test_IRoleEnumerationPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRoleEnumerationPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IRoleEnumerationPlugin.__name__ in listed)


class IRolesPlugin_conformance:

    def test_RolesPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRolesPlugin

        verifyClass( IRolesPlugin, self._getTargetClass() )

    def test_IRolesPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRolesPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IRolesPlugin.__name__ in listed)


class IRoleAssignerPlugin_conformance:

    def test_RoleAssignerPlugin_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRoleAssignerPlugin

        verifyClass( IRoleAssignerPlugin, self._getTargetClass() )

    def test_IRoleAssignerPlugin_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRoleAssignerPlugin

        listed = self._makeOne().listInterfaces()
        self.failUnless(IRoleAssignerPlugin.__name__ in listed)


class IChallengeProtocolChooser_conformance:

    def test_ChallengeProtocolChooser_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IChallengeProtocolChooser

        verifyClass( IChallengeProtocolChooser, self._getTargetClass() )

    def test_IChallengeProtocolChooser_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IChallengeProtocolChooser

        listed = self._makeOne().listInterfaces()
        self.failUnless(IChallengeProtocolChooser.__name__ in listed)


class IRequestTypeSniffer_conformance:

    def test_RequestTypeSniffer_conformance( self ):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRequestTypeSniffer

        verifyClass( IRequestTypeSniffer, self._getTargetClass() )

    def test_IRequestTypeSniffer_listInterfaces(self):

        from Products.PluggableAuthService.interfaces.plugins \
            import IRequestTypeSniffer

        listed = self._makeOne().listInterfaces()
        self.failUnless(IRequestTypeSniffer.__name__ in listed)


class IUserFolder_conformance:

    def test_conformance_IUserFolder( self ):

        from Products.PluggableAuthService.interfaces.authservice \
            import IUserFolder

        verifyClass( IUserFolder, self._getTargetClass() )


class IBasicUser_conformance:

    def test_conformance_IBasicUser( self ):

        from Products.PluggableAuthService.interfaces.authservice \
            import IBasicUser

        verifyClass( IBasicUser, self._getTargetClass() )


class IPropertiedUser_conformance:

    def test_conformance_IPropertiedUser( self ):

        from Products.PluggableAuthService.interfaces.authservice \
            import IPropertiedUser

        verifyClass( IPropertiedUser, self._getTargetClass() )


class IPropertySheet_conformance:

    def test_conformance_IPropertySheet( self ):

        from Products.PluggableAuthService.interfaces.propertysheets \
            import IPropertySheet

        verifyClass( IPropertySheet, self._getTargetClass() )

