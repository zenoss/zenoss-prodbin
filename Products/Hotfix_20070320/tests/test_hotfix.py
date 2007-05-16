import StringIO
from Testing.ZopeTestCase import FunctionalTestCase, user_name, user_password

class NoGETTest(FunctionalTestCase):
    def afterSetUp(self):
        self.folder_path = '/'+self.folder.absolute_url(1)
        self.setRoles(('Manager',))
        
    def _onlyPOST(self, path, qstring='', success=200, rpath=None):
        basic_auth = '%s:%s' % (user_name, user_password)
        env = dict()
        if rpath:
            env['HTTP_REFERER'] = self.app.absolute_url() + rpath
        response = self.publish('%s?%s' % (path, qstring), basic_auth, env)
        self.assertEqual(response.getStatus(), 403)
        
        data = StringIO.StringIO(qstring)
        response = self.publish(path, basic_auth, env, request_method='POST',
                                stdin=data)
        self.assertEqual(response.getStatus(), success)
    
    def test_userFolderAddUser(self):
        path = self.folder_path + '/acl_users/userFolderAddUser'
        qstring = 'name=foo&password=bar&domains=&roles:list=Manager'
        self._onlyPOST(path, qstring)
        
    def test_userFolderEditUser(self):
        path = self.folder_path + '/acl_users/userFolderEditUser'
        qstring = 'name=%s&password=bar&domains=&roles:list=Manager' % (
            user_name)
        self._onlyPOST(path, qstring)
        
    def test_userFolderDelUsers(self):
        path = self.folder_path + '/acl_users/userFolderDelUsers'
        qstring = 'names:list=%s' % user_name
        self._onlyPOST(path, qstring)
        
    def test_manage_setUserFolderProperties(self):
        path = self.folder_path + '/acl_users/manage_setUserFolderProperties'
        qstring = 'encrypt_passwords=1'
        self._onlyPOST(path, qstring)
        
    def test_addUser(self):
        # _addUser is called indirectly
        path = self.folder_path + '/acl_users/manage_users'
        qstring = ('submit=Add&name=foo&password=bar&confirm=bar&domains=&'
                   'roles:list=Manager')
        self._onlyPOST(path, qstring)
        
    def test_changeUser(self):
        # _changeUser is called indirectly
        path = self.folder_path + '/acl_users/manage_users'
        qstring = ('submit=Change&name=%s&password=bar&confirm=bar&domains=&'
                   'roles:list=Manager' % user_name)
        self._onlyPOST(path, qstring)
        
    def test_delUser(self):
        # _delUsers is called indirectly
        path = self.folder_path + '/acl_users/manage_users'
        qstring = ('submit=Delete&names:list=%s' % user_name)
        self._onlyPOST(path, qstring)
        
    def test_manage_takeOwnership(self):
        self.setRoles(('Owner',))
        path = self.folder_path + '/acl_users/manage_takeOwnership'
        rpath = self.folder_path + '/acl_users/manage_owner'
        self._onlyPOST(path, success=302, rpath=rpath)
       
    def test_manage_changeOwnershipType(self):
        self.setRoles(('Owner',))
        path = self.folder_path + '/acl_users/manage_changeOwnershipType'
        self._onlyPOST(path, success=302)
        
    def test_manage_setPermissionMapping(self):
        path = self.folder_path + '/manage_setPermissionMapping'
        qstring = 'permission_names:list=Foo&class_permissions:list=View'
        self._onlyPOST(path, qstring)
        
    def test_manage_acquiredPermissions(self):
        path = self.folder_path + '/manage_acquiredPermissions'
        qstring = 'permissions:list=View'
        self._onlyPOST(path, qstring)
        
    def test_manage_permission(self):
        path = self.folder_path + '/manage_permission'
        qstring = 'permission_to_manage=View&roles:list=Manager'
        self._onlyPOST(path, qstring)
        
    def test_manage_changePermissions(self):
        path = self.folder_path + '/manage_changePermissions'
        self._onlyPOST(path)
        
    def test_manage_addLocalRoles(self):
        path = self.folder_path + '/manage_addLocalRoles'
        qstring = 'userid=Foo&roles:list=Manager'
        self._onlyPOST(path, qstring)
        
    def test_manage_setLocalRoles(self):
        path = self.folder_path + '/manage_setLocalRoles'
        qstring = 'userid=Foo&roles:list=Manager'
        self._onlyPOST(path, qstring)
        
    def test_manage_delLocalRoles(self):
        path = self.folder_path + '/manage_delLocalRoles'
        qstring = 'userids:list=Foo'
        self._onlyPOST(path, qstring)
        
    def test_addRole(self):
        # _addRole is called indirectly
        path = self.folder_path + '/manage_defined_roles'
        qstring = 'submit=Add+Role&role=Foo'
        self._onlyPOST(path, qstring)
        
    def test_delRoles(self):
        # _delRoles is called indirectly
        path = self.folder_path + '/manage_defined_roles'
        qstring = 'submit=Delete+Role&role=Foo'
        self._onlyPOST(path, qstring)
        
    def test_DTMLMethod_manage_proxy(self):
        self.folder.addDTMLMethod('dtmlmethod')
        path = self.folder_path + '/dtmlmethod/manage_proxy'
        qstring = 'roles:list=Manager'
        self._onlyPOST(path, qstring)
        
    def test_PythonScript_manage_proxy(self):
        from Testing.ZopeTestCase import installProduct
        installProduct('PythonScripts')
        dispatcher = self.folder.manage_addProduct['PythonScripts']
        dispatcher.manage_addPythonScript('pythonscript')
        path = self.folder_path + '/pythonscript/manage_proxy'
        qstring = 'roles:list=Manager'
        self._onlyPOST(path, qstring)

def test_suite():
    from unittest import makeSuite
    return makeSuite(NoGETTest)

if __name__ == '__main__':
    import unittest
    unittest.main()
