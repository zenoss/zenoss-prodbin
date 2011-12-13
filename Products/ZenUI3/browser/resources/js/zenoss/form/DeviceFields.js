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

    var ZD = Ext.ns('Zenoss.devices');

    Ext.define("Zenoss.form.SmartCombo", {
        extend: "Ext.form.ComboBox",
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                store: new Zenoss.DirectStore({
                    directFn: config.directFn,
                    root: config.root || 'data',
                    fields: config.fields || ['name', 'value'],
                    initialSortColumn: config.initialSortColumn || 'name'
                }),
                valueField: 'value',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                autoSelect: true,
                selectOnFocus: false,
                triggerAction: 'all'
            });
            this.callParent([config]);
            if (this.autoLoad!==false) {
                this.getStore().load();
            }
        },        
        getValue: function() {
            return this.callParent(arguments) || this.getRawValue();
        },
        getStore: function() {
            return this.store;
        }
    });


    Ext.define("Zenoss.devices.PriorityCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.PriorityCombo'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                //fieldLabel: _t('Priority'),
                directFn: Zenoss.remote.DeviceRouter.getPriorities
            });
            this.callParent([config]);
        }
    });



    Ext.define("Zenoss.devices.DevicePriorityMultiselectMenu", {
        extend:"Zenoss.MultiselectMenu",
        alias: ['widget.multiselect-devicepriority'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                text:'...',              
                store: new Zenoss.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getPriorities,
                    root: 'data',
                    autoLoad: false,
                    initialSortColumn: 'name',
                    fields: ['name', 'value']
                }),
                defaultValues: []
            });
            ZD.DevicePriorityMultiselectMenu.superclass.constructor.call(this, config);
        }
    });

    Ext.define("Zenoss.devices.ProductionStateCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.ProductionStateCombo'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                //fieldLabel: _t('Production State'),
                directFn: Zenoss.remote.DeviceRouter.getProductionStates
            });
            this.callParent([config]);
        }
    });



    Ext.define("Zenoss.devices.ProductionStateMultiselectMenu", {
        extend:"Zenoss.MultiselectMenu",
        alias: ['widget.multiselect-prodstate'],
        constructor: function(config) {
            var defaults = [];
            if (Ext.isDefined(Zenoss.env.PRODUCTION_STATES)) {
                defaults = Ext.pluck(Zenoss.env.PRODUCTION_STATES.data, 'value');
            }
            config = Ext.apply(config || {}, {
                text:'...',
                ui:'arrowslide',
                store: new Zenoss.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getProductionStates,
                    root: 'data',
                    initialSortColumn: 'name',
                    autoLoad: false,
                    fields: ['name', 'value']
                }),
                defaultValues: defaults
            });
            ZD.ProductionStateMultiselectMenu.superclass.constructor.call(this, config);
        }
    });


    Ext.define("Zenoss.devices.ManufacturerDataStore", {
        extend:"Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'manufacturers',
                totalProperty: 'totalCount',
                fields: ['name'],
                initialSortColumn: 'name',
                directFn: router.getManufacturerNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.OSProductDataStore", {
        extend:"Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                fields: ['name'],
                initialSortColumn: 'name',
                directFn: router.getOSProductNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.HWProductDataStore", {
        extend:"Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                fields: ['name'],
                initialSortColumn: 'name',
                directFn: router.getHardwareProductNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.ManufacturerCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.manufacturercombo'],
        constructor: function(config) {
            var store = (config||{}).store || new ZD.ManufacturerDataStore();
            config = Ext.applyIf(config||{}, {
                store: store,
                width: 160
            });
            this.callParent([config]);
        }
    });


    Ext.define("Zenoss.devices.ProductCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.productcombo'],
        constructor: function(config) {
            var prodType = config.prodType || 'OS',
                store = (config||{}).store ||
                    prodType=='OS' ? new ZD.OSProductDataStore() : new ZD.HWProductDataStore();
            config = Ext.applyIf(config||{}, {
                store: store,
                width: 160
            });
            this.callParent([config]);
        }
    });

}());
