/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 or (at your
 # option) any later version as published by the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

/* package level */
(function() {
     // NOTE: All permissions are handled on the server, this is just to
     // enhance the user experience
     Ext.ns('Zenoss.Security');

     // Defined in ZenUI3/security/security.py this is a dictionary of all the
     // permissions the current user has on the current context.
     var all_permissions = _global_permissions(),
         callbacks = [];

     /**
      * The main method for ACL on the front end. It asks
      * if the current user has this permission.
      * The permissions are defined in Zope
      *
      * NOTE: The permissions are not case-sensitive here
      * @returns True/False if the user has permission or not
      **/
     Zenoss.Security.hasPermission = function(permission) {
         // uses all_permissions as a closure
         return all_permissions[permission.toLowerCase()];
     };

     /**
      * Asks if the current user has this permission in the
      * global context.
      * @returns True/False if the user has the permission or not
      **/
     Zenoss.Security.hasGlobalPermission = function(permission) {
         return _global_permissions()[permission.toLowerCase()];
     };

     /**
      * Convenience method, it makes the Hide and Disable properties
      * easier to read.
      * For instance:
      *      config {
      *           hidden: Zenoss.Security.doesNotHavePermission('Manage DMD');
      *      };
      * @returns True if the user does NOT have permission
      **/
     Zenoss.Security.doesNotHavePermission = function(permission) {
         return (!this.hasPermission(permission));
     };

     /**
      * Add an callback to be executed every time the permissions
      * are changed, usually this is done by changing context.
      * Example Usage:
      *     Zenoss.Security.onPermissionChange(function() {
      *         Ext.getCmp('foo').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
      * });
      *@param callback: function to execute
      *@param scope[Optional]: scope of the callback
      **/
     Zenoss.Security.onPermissionsChange = function(callback, scope) {
         if (scope) {
             callbacks.push(Ext.bind(callback, scope));
         }else {
             callbacks.push(callback);
         }
     };

     /**
      * If the context you are working on changes call this
      * method to update the security permissions for that new context
      **/
     Zenoss.Security.setContext = function(uid) {
         var params = {
             uid:uid
         };
         function callback(response) {
             var i;
             if (response.success) {
                 all_permissions = response.data;
                 if (callbacks) {
                     for (i = 0; i < callbacks.length; i += 1) {
                         callbacks[i]();
                     }
                 }
             }
         }
         Zenoss.remote.DetailNavRouter.getSecurityPermissions(params, callback);

     };

}());
