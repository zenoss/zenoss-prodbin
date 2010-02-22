/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 as published by
 # the Free Software Foundation.
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
     var all_permissions = _global_permissions();

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
        
}());