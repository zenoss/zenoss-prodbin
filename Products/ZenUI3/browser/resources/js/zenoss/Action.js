/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function() {
    Ext.ns('Zenoss.Action');

    Ext.define('Zenoss.PermissionableAction', {

        setPermission: function(config) {
            var me = this;
            // if they set the permissions config property
            // and the logged in user does not have permission, hide this element
            if (config.permission){
                var permission = config.permission;
                config.disabled = Zenoss.Security.doesNotHavePermission(permission);

                // register the control to be disabled or enabled based on the current context
                if (config.permissionContext) {
                    Zenoss.Security.onPermissionsChange(function(){
                        var cmp = me, uid = Zenoss.env.PARENT_CONTEXT;
                        if (uid == config.permissionContext) {
                            cmp.setDisabled(Zenoss.Security.doesNotHavePermission(permission));
                        } else {
                            cmp.setDisabled(!Zenoss.Security.hasGlobalPermission(permission));
                        }
                    });
                } else {
                    // update when the context changes
                    Zenoss.Security.onPermissionsChange(function(){
                        this.setDisabled(Zenoss.Security.doesNotHavePermission(permission));
                    }, this);
                }
            }


        }

    });

    function setDisabled(disable){
        var enable = !disable;
        if (disable || (Ext.isDefined(this.initialConfig.permission) && enable &&
                        Zenoss.Security.hasPermission(this.initialConfig.permission)===true)) {
            this.callParent([disable]);
        }
    }

    Ext.define("Zenoss.Action", {
        extend: "Ext.menu.Item",
        alias: ['widget.Action'],
        mixins: {
            permissions: 'Zenoss.PermissionableAction'
        },
        constructor: function(config){
            this.setPermission(config);
            this.callParent([config]);
        },
        setDisabled: setDisabled
    });

    Ext.define("Zenoss.ActionButton", {
        extend: "Ext.button.Button",
        alias: ['widget.buttonaction'],
        mixins: {
            permissions: 'Zenoss.PermissionableAction'
        },
        constructor: function(config){
            this.setPermission(config);
            this.callParent([config]);
        },
        setDisabled: setDisabled
    });
}());
