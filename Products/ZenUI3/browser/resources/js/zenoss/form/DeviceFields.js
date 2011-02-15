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

    var ZD = Ext.ns('Zenoss.devices');

    ZD.PriorityCombo = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                fieldLabel: _t('Priority'),
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getPriorities,
                    root: 'data',
                    fields: ['name', 'value']
                }),
                valueField: 'value',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                autoSelect: true,
                triggerAction: 'all'
            });
            ZD.PriorityCombo.superclass.constructor.call(this, config);
        }
    });

    Ext.reg('PriorityCombo', ZD.PriorityCombo);

    ZD.DevicePriorityMultiselectMenu = Ext.extend(Zenoss.MultiselectMenu, {
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                text:'...',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getPriorities,
                    root: 'data',
                    fields: ['name', 'value']
                }),
                defaultValues: []
            });
            ZD.DevicePriorityMultiselectMenu.superclass.constructor.call(this, config);
        }
    });

    Ext.reg('multiselect-devicepriority', ZD.DevicePriorityMultiselectMenu);

    ZD.ProductionStateCombo = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                fieldLabel: _t('Production State'),
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getProductionStates,
                    root: 'data',
                    fields: ['name', 'value']
                }),
                valueField: 'value',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                autoSelect: true,
                triggerAction: 'all'
            });
            ZD.ProductionStateCombo.superclass.constructor.call(this, config);

        }
    });

    Ext.reg('ProductionStateCombo', ZD.ProductionStateCombo);

    ZD.ProductionStateMultiselectMenu = Ext.extend(Zenoss.MultiselectMenu, {
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                text:'...',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getProductionStates,
                    root: 'data',
                    fields: ['name', 'value']
                }),
                defaultValues: ['1000']
            });
            ZD.ProductionStateMultiselectMenu.superclass.constructor.call(this, config);
        }
    });

    Ext.reg('multiselect-prodstate', ZD.ProductionStateMultiselectMenu);

    ZD.ManufacturerDataStore = Ext.extend(Ext.data.DirectStore, {
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'manufacturers',
                totalProperty: 'totalCount',
                fields: ['name'],
                directFn: router.getManufacturerNames
            });
            ZD.ManufacturerDataStore.superclass.constructor.call(this, config);
        }
    });

    ZD.OSProductDataStore = Ext.extend(Ext.data.DirectStore, {
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                fields: ['name'],
                directFn: router.getOSProductNames
            });
            ZD.ManufacturerDataStore.superclass.constructor.call(this, config);
        }
    });

    ZD.HWProductDataStore = Ext.extend(Ext.data.DirectStore, {
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                fields: ['name'],
                directFn: router.getHardwareProductNames
            });
            ZD.ManufacturerDataStore.superclass.constructor.call(this, config);
        }
    });

    ZD.ManufacturerCombo = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            var store = (config||{}).store || new ZD.ManufacturerDataStore();
            config = Ext.applyIf(config||{}, {
                store: store,
                triggerAction: 'all',
                selectOnFocus: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                width: 160
            });
            ZD.ManufacturerCombo.superclass.constructor.call(this, config);
        }
    });
    Ext.reg('manufacturercombo', ZD.ManufacturerCombo);

    ZD.ProductCombo = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            var prodType = config.prodType || 'OS',
                store = (config||{}).store || 
                    prodType=='OS' ? new ZD.OSProductDataStore() : new ZD.HWProductDataStore();
            config = Ext.applyIf(config||{}, {
                store: store,
                triggerAction: 'all',
                selectOnFocus: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                width: 160
            });
            ZD.ProductCombo.superclass.constructor.call(this, config);
        }
    });
    Ext.reg('productcombo', ZD.ProductCombo);


}());
