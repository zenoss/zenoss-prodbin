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
import unittest

from Products.PluggableAuthService.tests.conformance \
    import IAuthenticationPlugin_conformance
from Products.PluggableAuthService.tests.conformance \
    import IUserEnumerationPlugin_conformance
from Products.PluggableAuthService.tests.conformance \
    import IUserAdderPlugin_conformance

class DummyUser:

    def __init__( self, id ):
        self._id = id

    def getId( self ):
        return self._id

class ZODBUserManagerTests( unittest.TestCase
                          , IAuthenticationPlugin_conformance
                          , IUserEnumerationPlugin_conformance
                          , IUserAdderPlugin_conformance
                          ):

    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.ZODBUserManager \
            import ZODBUserManager

        return ZODBUserManager

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id=id, *args, **kw )

    def test_empty( self ):

        zum = self._makeOne()

        self.assertEqual( len( zum.listUserIds() ), 0 )
        self.assertEqual( len( zum.enumerateUsers() ), 0 )
        self.assertRaises( KeyError
                         , zum.getUserIdForLogin, 'userid@example.com' )
        self.assertRaises( KeyError
                         , zum.getLoginForUserId, 'userid' )

    def test_addUser( self ):

        zum = self._makeOne()

        zum.addUser( 'userid', 'userid@example.com', 'password' )

        user_ids = zum.listUserIds()
        self.assertEqual( len( user_ids ), 1 )
        self.assertEqual( user_ids[0], 'userid' )
        self.assertEqual( zum.getUserIdForLogin( 'userid@example.com' )
                        , 'userid' )
        self.assertEqual( zum.getLoginForUserId( 'userid' )
                        , 'userid@example.com' )

        info_list = zum.enumerateUsers()
        self.assertEqual( len( info_list ), 1 )
        info = info_list[ 0 ]
        self.assertEqual( info[ 'id' ], 'userid' )
        self.assertEqual( info[ 'login' ], 'userid@example.com' )

    def test_addUser_duplicate_check( self ):

        zum = self._makeOne()

        zum.addUser( 'userid', 'userid@example.com', 'password' )

        self.assertRaises( KeyError, zum.addUser
                         , 'userid', 'luser@other.com', 'wordpass' )

        self.assertRaises( KeyError, zum.addUser
                         , 'new_user', 'userid@example.com', '3733t' )

    def test_removeUser_nonesuch( self ):

        zum = self._makeOne()

        self.assertRaises( KeyError, zum.removeUser, 'nonesuch' )

    def test_removeUser_valid_id( self ):

        zum = self._makeOne()

        zum.addUser( 'userid', 'userid@example.com', 'password' )
        zum.addUser( 'doomed', 'doomed@example.com', 'password' )

        zum.removeUser( 'doomed' )

        user_ids = zum.listUserIds()
        self.assertEqual( len( user_ids ), 1 )
        self.assertEqual( len( zum.enumerateUsers() ), 1 )
        self.assertEqual( user_ids[0], 'userid' )

        self.assertEqual( zum.getUserIdForLogin( 'userid@example.com' )
                        , 'userid' )
        self.assertEqual( zum.getLoginForUserId( 'userid' )
                        , 'userid@example.com' )

        self.assertRaises( KeyError
                         , zum.getUserIdForLogin, 'doomed@example.com' )
        self.assertRaises( KeyError
                         , zum.getLoginForUserId, 'doomed' )

    def test_authenticateCredentials_bad_creds( self ):

        zum = self._makeOne()

        zum.addUser( 'userid', 'userid@example.com', 'password' )

        self.assertEqual( zum.authenticateCredentials( {} ), None )

    def test_authenticateCredentials_valid_creds( self ):

        zum = self._makeOne()

        zum.addUser( 'userid', 'userid@example.com', 'password' )

        user_id, login = zum.authenticateCredentials(
                                { 'login' : 'userid@example.com'
                                , 'password' : 'password'
                                } )

        self.assertEqual( user_id, 'userid' )
        self.assertEqual( login, 'userid@example.com' )

    def test_enumerateUsers_no_criteria( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='no_crit' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zum.addUser( id, '%s@example.com' % id, 'password' )

        info_list = zum.enumerateUsers()

        self.assertEqual( len( info_list ), len( ID_LIST ) )

        sorted = list( ID_LIST )
        sorted.sort()

        for i in range( len( sorted ) ):

            self.assertEqual( info_list[ i ][ 'id' ], sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'login' ]
                            , '%s@example.com' % sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'pluginid' ], 'no_crit' )
            self.assertEqual( info_list[ i ][ 'editurl' ]
                            , 'no_crit/manage_users?user_id=%s' % sorted[ i ])

    def test_enumerateUsers_exact( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='exact' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zum.addUser( id, '%s@example.com' % id, 'password' )

        info_list = zum.enumerateUsers( id='bar', exact_match=True )

        self.assertEqual( len( info_list ), 1 )
        info = info_list[ 0 ]

        self.assertEqual( info[ 'id' ], 'bar' )
        self.assertEqual( info[ 'login' ], 'bar@example.com' )
        self.assertEqual( info[ 'pluginid' ], 'exact' )
        self.assertEqual( info[ 'editurl' ]
                        , 'exact/manage_users?user_id=bar' )


    def test_enumerateUsers_partial( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='partial' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zum.addUser( id, '%s@example.com' % id, 'password' )

        info_list = zum.enumerateUsers( login='example.com', exact_match=False )

        self.assertEqual( len( info_list ), len( ID_LIST ) ) # all match

        sorted = list( ID_LIST )
        sorted.sort()

        for i in range( len( sorted ) ):

            self.assertEqual( info_list[ i ][ 'id' ], sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'login' ]
                            , '%s@example.com' % sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'pluginid' ], 'partial' )
            self.assertEqual( info_list[ i ][ 'editurl' ]
                            , 'partial/manage_users?user_id=%s' % sorted[ i ])

        info_list = zum.enumerateUsers( id='ba', exact_match=False )

        self.assertEqual( len( info_list ), len( ID_LIST ) - 1 ) # no 'foo'

        sorted = list( ID_LIST )
        sorted.sort()

        for i in range( len( sorted ) - 1 ):

            self.assertEqual( info_list[ i ][ 'id' ], sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'login' ]
                            , '%s@example.com' % sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'pluginid' ], 'partial' )
            self.assertEqual( info_list[ i ][ 'editurl' ]
                            , 'partial/manage_users?user_id=%s' % sorted[ i ])

    def test_enumerateUsers_exact_nonesuch( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='exact_nonesuch' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zum.addUser( id, '%s@example.com' % id, 'password' )

        self.assertEquals( zum.enumerateUsers( id='qux', exact_match=True )
                         , () )

    def test_enumerateUsers_multiple_ids( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='partial' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zum.addUser( id, '%s@example.com' % id, 'password' )

        info_list = zum.enumerateUsers( id=ID_LIST )

        self.assertEqual( len( info_list ), len( ID_LIST ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in ID_LIST )

        SUBSET = ID_LIST[:3]

        info_list = zum.enumerateUsers( id=SUBSET )

        self.assertEqual( len( info_list ), len( SUBSET ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in SUBSET )

    def test_enumerateUsers_multiple_logins( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zum = self._makeOne( id='partial' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )
        LOGIN_LIST = [ '%s@example.com' % x for x in ID_LIST ]

        for i in range( len( ID_LIST ) ):

            zum.addUser( ID_LIST[i], LOGIN_LIST[i], 'password' )

        info_list = zum.enumerateUsers( login=LOGIN_LIST )

        self.assertEqual( len( info_list ), len( LOGIN_LIST ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in ID_LIST )
            self.failUnless( info[ 'login' ] in LOGIN_LIST )

        SUBSET_LOGINS = LOGIN_LIST[:3]
        SUBSET_IDS = ID_LIST[:3]

        info_list = zum.enumerateUsers( login=SUBSET_LOGINS )

        self.assertEqual( len( info_list ), len( SUBSET_LOGINS ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in SUBSET_IDS )
            self.failUnless( info[ 'login' ] in SUBSET_LOGINS )

    def test_authenticateWithOldPasswords( self ):

        import sha

        zum = self._makeOne()

        # synthesize an older account

        old_password = sha.sha( 'old_password' ).hexdigest()
        zum._user_passwords[ 'old_user' ] = old_password
        zum._login_to_userid[ 'old_user@example.com' ] = 'old_user'
        zum._userid_to_login[ 'old_user' ] = 'old_user@example.com'

        # create a new user

        zum.addUser( 'new_user', 'new_user@example.com', 'new_password' )

        user_id, login = zum.authenticateCredentials(
                                { 'login' : 'old_user@example.com'
                                , 'password' : 'old_password'
                                } )

        self.assertEqual( user_id, 'old_user' )
        self.assertEqual( login, 'old_user@example.com' )

        user_id, login = zum.authenticateCredentials(
                                { 'login' : 'new_user@example.com'
                                , 'password' : 'new_password'
                                } )

        self.assertEqual( user_id, 'new_user' )
        self.assertEqual( login, 'new_user@example.com' )

    def test_updateUserPassword(self):

        zum = self._makeOne()

        # Create a user and make sure we can authenticate with it
        zum.addUser( 'user1', 'user1@example.com', 'password' )
        info1 = { 'login' : 'user1@example.com', 'password' : 'password' }
        user_id, login = zum.authenticateCredentials(info1)
        self.assertEqual(user_id, 'user1')
        self.assertEqual(login, 'user1@example.com')

        # Give the user a new password; attempting to authenticate with the
        # old password must fail
        zum.updateUserPassword('user1', 'new_password')
        self.failIf(zum.authenticateCredentials(info1))

        # Try to authenticate with the new password, this must succeed.
        info2 = { 'login' : 'user1@example.com', 'password' : 'new_password' }
        user_id, login = zum.authenticateCredentials(info2)
        self.assertEqual(user_id, 'user1')
        self.assertEqual(login, 'user1@example.com')

    def test_updateUser(self):

        zum = self._makeOne()

        # Create a user and make sure we can authenticate with it
        zum.addUser( 'user1', 'user1@example.com', 'password' )
        info1 = { 'login' : 'user1@example.com', 'password' : 'password' }
        user_id, login = zum.authenticateCredentials(info1)
        self.assertEqual(user_id, 'user1')
        self.assertEqual(login, 'user1@example.com')

        # Give the user a new login; attempts to authenticate with the
        # old login must fail.
        zum.updateUser('user1', 'user1@foobar.com')
        self.failIf(zum.authenticateCredentials(info1))

        # Try to authenticate with the new login, this must succeed.
        info2 = { 'login' : 'user1@foobar.com', 'password' : 'password' }
        user_id, login = zum.authenticateCredentials(info2)
        self.assertEqual(user_id, 'user1')
        self.assertEqual(login, 'user1@foobar.com')

    def test_enumerateUsersWithOptionalMangling(self):

        zum = self._makeOne()
        zum.prefix = 'special__'

        zum.addUser('user', 'login', 'password')
        info = zum.enumerateUsers(login='login')
        self.assertEqual(info[0]['id'], 'special__user')

    def test_getUserByIdWithOptionalMangling(self):

        zum = self._makeOne()
        zum.prefix = 'special__'

        zum.addUser('user', 'login', 'password')

        info = zum.enumerateUsers(id='user', exact_match=True)
        self.assertEqual(len(info), 0)

        info = zum.enumerateUsers(id='special__user', exact_match=True)
        self.assertEqual(info[0]['id'], 'special__user')

        info = zum.enumerateUsers(id='special__luser', exact_match=True)
        self.assertEqual(len(info), 0)

    def test_addUser_with_not_yet_encrypted_password(self):
        # See collector #1869 && #1926
        from AccessControl.AuthEncoding import is_encrypted

        USER_ID = 'not_yet_encrypted'
        PASSWORD = 'password'

        self.failIf(is_encrypted(PASSWORD))

        zum = self._makeOne()
        zum.addUser(USER_ID, USER_ID, PASSWORD)

        uid_and_info = zum.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))

    def test_addUser_with_preencrypted_password(self):
        # See collector #1869 && #1926
        from AccessControl.AuthEncoding import pw_encrypt

        USER_ID = 'already_encrypted'
        PASSWORD = 'password'

        ENCRYPTED = pw_encrypt(PASSWORD)

        zum = self._makeOne()
        zum.addUser(USER_ID, USER_ID, ENCRYPTED)

        uid_and_info = zum.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))

    def test_updateUserPassword_with_not_yet_encrypted_password(self):
        from AccessControl.AuthEncoding import is_encrypted

        USER_ID = 'not_yet_encrypted'
        PASSWORD = 'password'

        self.failIf(is_encrypted(PASSWORD))

        zum = self._makeOne()
        zum.addUser(USER_ID, USER_ID, '')
        zum.updateUserPassword(USER_ID, PASSWORD)

        uid_and_info = zum.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))

    def test_updateUserPassword_with_preencrypted_password(self):
        from AccessControl.AuthEncoding import pw_encrypt

        USER_ID = 'already_encrypted'
        PASSWORD = 'password'

        ENCRYPTED = pw_encrypt(PASSWORD)

        zum = self._makeOne()
        zum.addUser(USER_ID, USER_ID, '')
        zum.updateUserPassword(USER_ID, ENCRYPTED)

        uid_and_info = zum.authenticateCredentials(
                                { 'login': USER_ID
                                , 'password': PASSWORD
                                })

        self.assertEqual(uid_and_info, (USER_ID, USER_ID))


if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( ZODBUserManagerTests ),
        ))
