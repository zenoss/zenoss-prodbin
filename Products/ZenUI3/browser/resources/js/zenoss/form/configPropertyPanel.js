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

(function(){
    var router = Zenoss.remote.DeviceRouter,
        ConfigPropertyGrid,
        ConfigPropertyPanel,
        zpropertyConfigs = {};

    Ext.ns('Zenoss.zproperties');
    Ext.apply(zpropertyConfigs, {
        'int': {
            xtype: 'numberfield',
            allowDecimals: false
        },
        'float': {
            xtype: 'numberfield'
        },
        'string': {
            xtype: 'textfield'
        },
        'lines': {
            xtype: 'textarea'
        },
        'severity': {
            xtype: 'severity'
        },
        'boolean': {
            xtype: 'checkbox'
        },
        'password': {
            xtype: 'password'
        },
        'options': {
            xtype: 'combo',
            editable: false,
            forceSelection: true,
            autoSelect: true,
            triggerAction: 'all',
            mode: 'local'
        },
        'zSnmpCommunity': {
            xtype: Zenoss.Security.doesNotHavePermission('zProperties Edit') ? 'password' : 'textfield'
        },
        'zEventSeverity': {
            xtype: 'severity'
        },
        'zFailSeverity': {
            xtype: 'severity'
        },
        'zWinEventlogMinSeverity': {
            xtype: 'reverseseverity'
        }
    });

    /**
     * Allow zenpack authors to register custom zproperty
     * editors.
     **/
    Zenoss.zproperties.registerZPropertyType = function(id, config){
        zpropertyConfigs[id] = config;
    };


    function showEditConfigPropertyDialog(data, grid) {
        var handler, uid, config, editConfig, dialog, type;
        uid = grid.uid;
        type = data.type;
        // Try the specific property id, next the type and finall default to string
        editConfig = zpropertyConfigs[data.id] || zpropertyConfigs[type] || zpropertyConfigs['string'];

        // in case of drop down lists
        if (Ext.isArray(data.options) && data.options.length > 0 && type == 'string') {
            // make it a combo and the options is the store
            editConfig = zpropertyConfigs['options'];
            editConfig.store = data.options;
        }

        // set the default values common to all configs
        Ext.apply(editConfig, {
            fieldLabel: _t('Value'),
            value: data.value,
            ref: 'editConfig',
            checked: data.value,
            name: data.id
        });

        // lines come in as comma separated and should be saved as such
        if (type == 'lines' && Ext.isArray(editConfig.value)){
            editConfig.value = editConfig.value.join('\n');
        }

        handler = function() {
            // save the junk and reload
            var values = dialog.getForm().getForm().getFieldValues(),
                value = values[data.id];
            if (type == 'lines') {
                // send back as an array separated by a new line
                value = value.split('\n');
            }
            var params = {
                uid: grid.uid,
                zProperty: data.id,
                value: value
            };
            Zenoss.remote.DeviceRouter.setZenProperty(params, function(response){
                if (response.success) {
                    grid.refresh();
                }
            });

        };

        // form config
        config = {
            submitHandler: handler,
            minHeight: 300,
            autoHeight: true,
            width: 500,
            title: _t('Edit Config Property'),
            listeners: {
                show: function() {
                    dialog.getForm().query("field[ref='editConfig']")[0].focus(true, 500);
                }
            },
            items: [{
                    xtype: 'displayfield',
                    name: 'name',
                    fieldLabel: _t('Name'),
                    value: data.id
                },{
                    xtype: 'displayfield',
                    name: 'path',
                    ref: 'path',
                    fieldLabel: _t('Path'),
                    value: data.path
                },{
                    xtype: 'displayfield',
                    name: 'type',
                    ref: 'type',
                    fieldLabel: _t('Type'),
                    value: data.type
                }, editConfig
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {

            }
        };
        dialog = new Zenoss.SmartFormDialog(config);

        if (Zenoss.Security.hasPermission('zProperties Edit')) {
            dialog.show();
        }
    }

    /**
     * @class Zenoss.ConfigProperty.Model'
     * @extends Ext.data.Model
     * Field definitions for the Config Properties
     **/
    Ext.define('Zenoss.ConfigProperty.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'id'},
            {name: 'islocal'},
            {name: 'value'},
            {name: 'category'},
            {name: 'valueAsString'},
            {name: 'type'},
            {name: 'path'},
            {name: 'options'}
        ]
    });
    /**
     * @class Zenoss.ConfigProperty.Store
     * @extends Zenoss.DirectStore
     * Store for our configuration properties grid
     **/
    Ext.define("Zenoss.ConfigProperty.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.ConfigProperty.Model',
                initialSortColumn: 'id',
                directFn: Zenoss.remote.DeviceRouter.getZenProperties
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.ConfigProperty.Grid", {
        alias: ['widget.configpropertygrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                this.disableButtons(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'config_property_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                tbar:[
                     {
                        xtype: 'tbtext',
                        height:30,
                        text: _t('Configuration Properties')
                    },
                    '-',
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    toolTip: _t('Customize'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    ref: 'customizeButton',
                    handler: function(button) {
                        var grid = button.up("configpropertygrid"),
                            data,
                            selected = grid.getSelectionModel().getSelection();

                        if (Ext.isEmpty(selected)) {
                            return;
                        }
                        // single selection
                        data = selected[0].data;
                        showEditConfigPropertyDialog(data, grid);
                    }
                    }, {
                    xtype: 'button',
                    iconCls: 'refresh',
                        toolTip: _t('Refresh'),
                    ref: '../refreshButton',
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    handler: function(button) {
                        var grid = button.up("configpropertygrid");
                        grid.refresh();
                    }
                    },{
                        xtype: 'button',
                        ref: '../deleteButton',
                        toolTip: _t('Delete'),
                        text: _t('Delete Local Copy'),
                        handler: function(button) {
                            var grid = button.up("configpropertygrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            if (data.islocal && data.path == '/') {
                                Zenoss.message.info(_t('{0} can not be deleted from the root definition.'), data.id);
                                return;
                            }
                            if (!data.islocal){
                                Zenoss.message.info(_t('{0} is not defined locally'), data.id);
                                return;
                            }
                    new Zenoss.dialog.SimpleMessageDialog({
                        title: _t('Delete Local Property'),
                        message: String.format(_t("Are you sure you want to delete the local copy of {0}?"), data.id),                    
                        buttons: [{
                            xtype: 'DialogButton',
                            text: _t('OK'),
                            handler: function() {
                                        if (grid.uid) {
                                            router.deleteZenProperty({
                                                uid: grid.uid,
                                                zProperty: data.id
                                            }, function(response){
                                                grid.refresh();
                                            });
                                        }
                            }
                        }, {
                            xtype: 'DialogButton',
                            text: _t('Cancel')
                        }]
                    }).show();                                  
                        }
                    }
                ],
                store: Ext.create('Zenoss.ConfigProperty.Store', {
                }),
                columns: [{
                        header: _t("Is Local"),
                        id: 'islocal',
                        dataIndex: 'islocal',
                        width: 60,
                        sortable: true,
                        filter: false,
                        renderer: function(value){
                            if (value) {
                                return 'Yes';
                            }
                            return '';
                        }
                    },{
                        id: 'category',
                        dataIndex: 'category',
                        header: _t('Category'),
                        sortable: true
                    },{
                        id: 'id',
                        dataIndex: 'id',
                        header: _t('Name'),
                        width: 200,
                        sortable: true
                    },{
                        id: 'value',
                        dataIndex: 'valueAsString',
                        header: _t('Value'),
                        flex: 1,
                        width: 180,
                        renderer: function(v, row, record) {
                            if (Zenoss.Security.doesNotHavePermission("zProperties Edit") &&
                                record.data.id == 'zSnmpCommunity') {
                                return "*******";
                            }
                            return v;
                        },
                        sortable: false
                    },{
                        id: 'path',
                        dataIndex: 'path',
                        header: _t('Path'),
                        width: 200,
                        sortable: true
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {
            if (uid == '/zport/dmd/Devices'){
                this.deleteButton.setDisabled(true);
            } else {
                this.deleteButton.setDisabled(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }

            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        onRowDblClick: function(grid, rowIndex, e) {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            showEditConfigPropertyDialog(data, this);
        },
        disableButtons: function(bool) {
            var btns = this.query("button");
            Ext.each(btns, function(btn){
                btn.setDisabled(bool);
            });
        }
    });

    Ext.define("Zenoss.form.ConfigPropertyPanel", {
        alias:['widget.configpropertypanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            this.gridId = Ext.id();
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                height: 800,
                items: [{
                    id: this.gridId,
                    xtype: "configpropertygrid",
                    ref: 'configGrid',
                    displayFilters: config.displayFilters
                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            Ext.getCmp(this.gridId).setContext(uid);
        }
    });

})();