/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/* package level */
(function() {
    var ZF = Ext.ns('Zenoss.form'),
        router = Zenoss.remote.DeviceRouter,
        OrganizerDropDown,
        SystemDropDown,
        LocationDropDown,
        DeviceClassDropDown,
        GroupDropDown;

    Ext.define("Zenoss.form.OrganizerDropDown", {
        extend:"Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                xtype: 'combo',
                name: 'group',
                store: new Ext.data.DirectStore({
                    directFn: config.getGroupFn,
                    root: config.getGroupRoot,
                    fields: ['name']
                }),
                valueField: 'name',
                emptyText: _t('All...'),
                displayField: 'name',
                allowBlank: true,
                forceSelection: false,
                editable: true,
                autoSelect: true,
                triggerAction: 'all',
                listConfig: {
                    resizable: true
                }
            });
            Zenoss.form.OrganizerDropDown.superclass.constructor.apply(this, arguments);
        }
    });

    Ext.define("Zenoss.form.SystemDropDown", {
        alias:['widget.systemdropdown'],
        extend:"Zenoss.form.OrganizerDropDown",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getSystems,
                getGroupRoot: 'systems'
            });
            Zenoss.form.SystemDropDown.superclass.constructor.apply(this, arguments);
        }
    });


    Ext.define("Zenoss.form.GroupDropDown", {
        alias:['widget.groupdropdown'],
        extend:"Zenoss.form.OrganizerDropDown",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getGroups,
                getGroupRoot: 'groups'
            });
            Zenoss.form.GroupDropDown.superclass.constructor.apply(this, arguments);
        }
    });


    Ext.define("Zenoss.form.LocationDropDown", {
        alias:['widget.locationdropdown'],
        extend:"Zenoss.form.OrganizerDropDown",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getLocations,
                getGroupRoot: 'locations'
            });
            Zenoss.form.LocationDropDown.superclass.constructor.apply(this, arguments);
        }
    });


    Ext.define("Zenoss.form.DeviceClassDropDown", {
        alias:['widget.deviceclassdropdown'],
        extend:"Zenoss.form.OrganizerDropDown",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getDeviceClasses,
                getGroupRoot: 'deviceClasses'
            });
            Zenoss.form.DeviceClassDropDown.superclass.constructor.apply(this, arguments);
        }
    });



}());
