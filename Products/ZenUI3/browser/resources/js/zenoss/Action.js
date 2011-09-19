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

(function() {
     Ext.ns('Zenoss.Action');

     Zenoss.Action = Ext.extend(Ext.Action, {
         constructor: function(config) {
             var me = this;
             // if they set the permissions config property
             // and the logged in user does not have permission, hide this element
             if (config.permission){
                 config.disabled = Zenoss.Security.doesNotHavePermission(config.permission);

                 // register the control to be disabled or enabled based on the current context
                 if (config.permissionContext) {
                     Zenoss.Security.onPermissionsChange(function(){
                         var cmp = me, uid = Zenoss.env.PARENT_CONTEXT;
                         if (uid == config.permissionContext) {
                             cmp.setDisabled(Zenoss.Security.doesNotHavePermission(config.permission));
                         } else {
                             cmp.setDisabled(!Zenoss.Security.hasGlobalPermission(config.permission));
                         }
                     });

                 }
             }

             // call the parent's constructor
             Zenoss.Action.superclass.constructor.apply(this, arguments);


         },
         setDisabled : function(disable){
             var enable = !disable;
             if (disable || (Ext.isDefined(this.initialConfig.permission) && enable &&
                     Zenoss.Security.hasPermission(this.initialConfig.permission)===true)) {
                 Zenoss.Action.superclass.setDisabled.apply(this, arguments);
             }
        }
     });

     Ext.reg('Action', Zenoss.Action);
}());
