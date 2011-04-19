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
        'zEventSeverity': {
            xtype: 'severity'
        },
        'zFailSeverity': {
            xtype: 'severity'
        },
        'zWinEventlogMinSeverity': {
            xtype: 'severity'
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
            var values = dialog.editForm.getForm().getFieldValues(),
                value = values[data.id];
            if (type == 'lines') {
                // send back as an array separated by a new line
                value = value.split('\n');
            }

            Zenoss.remote.DeviceRouter.setZenProperty({
                uid: grid.uid,
                zProperty: data.id,
                value: value
            }, function(response){
                if (response.success) {
                    var view = grid.getView();
                    view.updateLiveRows(
                        view.rowIndex, true, true);

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
                    dialog.editForm.editConfig.focus(true, 500);
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
                }, editConfig
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {

            }
        };
        dialog = new Zenoss.SmartFormDialog(config);
        dialog.show();
    }

    ConfigPropertyGrid = Ext.extend(Zenoss.FilterGridPanel, {
        constructor: function(config) {
            config = config || {};
            var view;
            if (!Ext.isDefined(config.displayFilters)
                || config.displayFilters
               ){
                view = new Zenoss.FilterGridView({
                    rowHeight: 22,
                    nearLimit: 100,
                    loadMask: {msg: _t('Loading. Please wait...')}
                });
            }else {
                view = new Ext.ux.grid.livegrid.GridView({
                    nearLimit: 100,
                    rowHeight: 22,
                    getState: function() {
                        return {};
                    },
                    loadMask: {msg: _t('Loading...'),
                          msgCls: 'x-mask-loading'}

                });
            }
            // register this control for when permissions change
            Zenoss.Security.onPermissionsChange(function() {
                this.disableButtons(Zenoss.Security.doesNotHavePermission('Manage DMD'));
            }, this);
            Ext.applyIf(config, {
                autoExpandColumn: 'value',
                stripeRows: true,
                stateId: config.id || 'config_property_grid',
                autoScroll: true,
                sm: new Zenoss.ExtraHooksSelectionModel({
                    singleSelect: true
                }),
                border: false,
                tbar:[
                     {
                        xtype: 'tbtext',
                        text: _t('Configuration Properties')
                    },
                    '-',
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    ref: '../customizeButton',
                    handler: function(button) {
                        var grid = button.refOwner,
                            data,
                            selected = grid.getSelectionModel().getSelected();
                        if (!selected) {
                            return;
                        }
                        data = selected.data;
                        showEditConfigPropertyDialog(data, grid);
                    }
                    }, {
                    xtype: 'button',
                    iconCls: 'refresh',
                    ref: '../refreshButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(button) {
                        var grid = button.refOwner;
                        var view = grid.getView();
                        view.updateLiveRows(
                            view.rowIndex, true, true);
                    }
                    },{
                        xtype: 'button',
                        ref: '../deleteButton',

                        text: _t('Delete Local Copy'),
                        handler: function(button) {
                            var grid = button.refOwner,
                                data,
                                selected = grid.getSelectionModel().getSelected();
                            if (!selected) {
                                return;
                            }

                            data = selected.data;
                            if (data.islocal && data.path == '/') {
                                Zenoss.message.info(_t('{0} can not be deleted from the root definition.'), data.id);
                                return;
                            }
                            if (!data.islocal){
                                Zenoss.message.info(_t('{0} is not defined locally'), data.id);
                                return;
                            }
                            Ext.Msg.show({
                            title: _t('Delete Local Property'),
                            msg: String.format(_t("Are you sure you want to delete the local copy of {0}?"), data.id),
                            buttons: Ext.Msg.OKCANCEL,
                            fn: function(btn) {
                                if (btn=="ok") {
                                    if (grid.uid) {
                                        router.deleteZenProperty({
                                            uid: grid.uid,
                                            zProperty: data.id
                                        }, function(response){
                                            var view = grid.getView();
                                            view.updateLiveRows(
                                                view.rowIndex, true, true);
                                        });
                                    }
                                } else {
                                    Ext.Msg.hide();
                                }
                            }
                        });
                        }
                    }
                ],
                store: new Ext.ux.grid.livegrid.Store({
                    bufferSize: 400,
                    autoLoad: true,
                    defaultSort: {field: 'id', direction:'ASC'},
                    sortInfo: {field: 'id', direction:'ASC'},
                    proxy: new Ext.data.DirectProxy({
                        directFn: Zenoss.remote.DeviceRouter.getZenProperties
                    }),
                    reader: new Ext.ux.grid.livegrid.JsonReader({
                        root: 'data',
                        totalProperty: 'totalCount',
                        idProperty: 'id'
                    },[
                        {name: 'id'},
                        {name: 'islocal'},
                        {name: 'value'},
                        {name: 'category'},
                        {name: 'valueAsString'},
                        {name: 'type'},
                        {name: 'path'},
                        {name: 'options'}
                    ])
                }),
                cm: new Ext.grid.ColumnModel({
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
                        width: 120,
                        sortable: true
                    },{
                        id: 'value',
                        dataIndex: 'valueAsString',
                        header: _t('Value'),
                        width: 180,
                        sortable: false
                    },{
                        id: 'path',
                        dataIndex: 'path',
                        header: _t('Path'),
                        width: 200,
                        sortable: true
                    }]
                }),
                view: view
            });
            ConfigPropertyGrid.superclass.constructor.apply(this, arguments);
            this.on('rowdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            // set the uid and load the grid
            var view = this.getView();
            view.contextUid  = uid;
            this.getStore().setBaseParam('uid', uid);
            this.getStore().load();
            if (uid == '/zport/dmd/Devices'){
                this.deleteButton.setDisabled(true);
            }
        },
        onRowDblClick: function(grid, rowIndex, e) {
            var data,
                selected = grid.getSelectionModel().getSelected();
            if (!selected) {
                return;
            }
            data = selected.data;
            showEditConfigPropertyDialog(data, grid);
        },
        disableButtons: function(bool) {
            this.deleteButton.setDisabled(bool);
            this.customizeButton.setDisabled(bool);
        }
    });

    ConfigPropertyPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                height: 800,
                items: [new ConfigPropertyGrid({
                    ref: 'configGrid',
                    displayFilters: config.displayFilters
                })]

            });
            ConfigPropertyPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.configGrid.setContext(uid);
        }
    });

    Ext.reg('configpropertypanel', ConfigPropertyPanel);

})();