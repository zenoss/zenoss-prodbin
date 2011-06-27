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
    var ZF = Ext.ns('Zenoss.form'),
        router = Zenoss.remote.DeviceRouter,
        OrganizerDropDown,
        SystemDropDown,
        LocationDropDown,
        DeviceClassDropDown,
        GroupDropDown;

    OrganizerDropDown = Ext.extend(Ext.form.ComboBox, {
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
                triggerAction: 'all'
            });
            OrganizerDropDown.superclass.constructor.apply(this, arguments);
        }
    });

    SystemDropDown = Ext.extend(OrganizerDropDown, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getSystems,
                getGroupRoot: 'systems'
            });
            SystemDropDown.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('systemdropdown', SystemDropDown);

    GroupDropDown = Ext.extend(OrganizerDropDown, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getGroups,
                getGroupRoot: 'groups'
            });
            GroupDropDown.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('groupdropdown', GroupDropDown);

    LocationDropDown = Ext.extend(OrganizerDropDown, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getLocations,
                getGroupRoot: 'locations'
            });
            LocationDropDown.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('locationdropdown', LocationDropDown);

    DeviceClassDropDown = Ext.extend(OrganizerDropDown, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                getGroupFn: router.getDeviceClasses,
                getGroupRoot: 'deviceClasses'
            });
            DeviceClassDropDown.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('deviceclassdropdown', DeviceClassDropDown);


}());