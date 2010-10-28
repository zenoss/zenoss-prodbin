/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.ns('Zenoss.ui.Triggers');

Ext.onReady(function(){
    

    var router = Zenoss.remote.TriggersRouter,
        colModelConfig,
        triggersPanelConfig,
        notificationsPanelConfig,
        detailPanelConfig,
        navSelectionModel,
        masterPanelConfig,
        AddTriggerDialogue,
        reloadTriggersGrid,
        displayEditTriggerDialogue,
        addTriggerDialogue,
        editTriggerDialogue,
        colModel,
        TriggersGridPanel,
        EditTriggerDialogue;
    
    
    colModelConfig = {
        defaults: {
            menuDisabled: true
        },
        columns: [
            {
                id: 'enabled',
                dataIndex: 'enabled',
                header: _t('Enabled'),
                xtype: 'booleancolumn',
                width: 70,
                sortable: true
            }, {
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                width: 200,
                sortable: true
            }, {
                id: 'delay',
                dataIndex: 'delay_seconds',
                header: _t('Delay'),
                xtype: 'numbercolumn',
                width: 70,
                format: '0',
                sortable: true
            }, {
                id: 'repeat',
                dataIndex: 'repeat_seconds',
                header: _t('Repeat'),
                xtype: 'numbercolumn',
                width: 70,
                format: '0',
                sortable: true
            }, {
                id: 'send_clear',
                dataIndex: 'send_clear',
                header: _t('Send Clear?'),
                xtype: 'booleancolumn',
                width: 110,
                sortable: true
            }
        ]
    };
    
    triggersPanelConfig = {
        id: 'triggers_grid_panel',
        'xtype': 'TriggersGridPanel'
    };
    
    notificationsPanelConfig = {
        id: 'notifications_panel',
        text: 'notifications',
        items: [
            {xtype:'button'}
        ]
    };
    
    // temp panel for testing, just a placeholder.
    var o2 = new Zenoss.PlaceholderPanel(notificationsPanelConfig);
    
    detailPanelConfig = {
        id: 'triggers_detail_panel',
        xtype: 'contextcardpanel',
        split: true,
        region: 'center',
        layout: 'card',
        activeItem: 0,
        items: [triggersPanelConfig, o2]
    };
    
    navSelectionModel = new Ext.tree.DefaultSelectionModel({
        listeners: {
            selectionchange: function (sm, newnode) {
                var p = Ext.getCmp(detailPanelConfig.id);
                p.layout.setActiveItem(newnode.attributes.target);
                p.setContext(newnode.attributes.target);
            }
        }
    });
    
    masterPanelConfig = {
        id: 'master_panel',
        region: 'west',
        split: 'true',
        width: 275,
        autoScroll: false,
        items: [
            {
                id: 'master_panel_navigation',
                xtype: 'treepanel',
                region: 'west',
                split: 'true',
                width: 275,
                autoScroll: true,
                border: false,
                rootVisible: false,
                selModel: navSelectionModel,
                layout: 'fit',
                bodyStyle: { 'margin-top' : 10 },
                root: {
                    text: 'Trigger Navigation',
                    draggable: false,
                    id: 'trigger_root',
                    expanded: true,
                    children: [
                        {
                            target: triggersPanelConfig.id,
                            text: 'Triggers',
                            leaf: true,
                            iconCls: 'no-icon'
                        }, {
                            target: notificationsPanelConfig.id,
                            text: 'Notifications',
                            leaf: true,
                            iconCls: 'no-icon'
                        }
                    ]
                }
            }
        ]
    };
    
    AddTriggerDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 150,
                width: 310,
                modal: true,
                plain: true,
                closeAction: 'hide',
                listeners: {
                    show: function(win) {
                        win.addForm.name.setValue('');
                    }
                },
                items:{
                    xtype:'form',
                    ref: 'addForm',
                    border: false,
                    buttonAlign: 'left',
                    monitorValid: true,
                    items:[{
                        xtype: 'textfield',
                        name: 'name',
                        ref: 'name',
                        allowBlank: false,
                        vtype: 'alphanum',
                        fieldLabel: _t('Name')
                    }],
                    buttons:[{
                        xtype: 'button',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        formBind: true,
                        handler: function(button) {
                            var params = {
                                name: button.refOwner.addForm.name.getValue()
                            };
                            config.directFn(params, function(){
                                button.refOwner.addForm.name.setValue('');
                                button.refOwner.hide();
                                config.reloadFn();
                            });
                        }
                    },{
                        xtype: 'button',
                        ref: '../../cancelButton',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.hide();
                        }
                    }]}
            });
            AddTriggerDialogue.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('addtriggerdialogue', AddTriggerDialogue);
    
    EditTriggerDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                border: false,
                closeAction: 'hide',
                listeners: {
                    show: function(win) {
                        // empty form values
                    }
                },
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'left',
                    monitorValid: true,
                    items:[
                        {
                            xtype: 'hidden',
                            name: 'uuid',
                            ref: 'uuid'
                        },{
                            xtype: 'textfield',
                            name: 'name',
                            ref: 'name',
                            allowBlank: false,
                            fieldLabel: _t('Name')
                        },{
                            xtype: 'numberfield',
                            name: 'delay_seconds',
                            ref: 'delay_seconds',
                            allowBlank: true,
                            allowNegative: false,
                            allowDecimals: false,
                            fieldLabel: _t('Delay (seconds)')
                        },{
                            xtype: 'numberfield',
                            name: 'repeat_seconds',
                            ref: 'repeat_seconds',
                            allowBlank: true,
                            allowNegative: false,
                            allowDecimals: false,
                            fieldLabel: _t('Repeat (seconds)')
                        },{
                            xtype: 'checkbox',
                            name: 'enabled',
                            ref: 'enabled',
                            fieldLabel: _t('Enabled')
                        },{
                            xtype: 'checkbox',
                            name: 'send_clear',
                            ref: 'send_clear',
                            fieldLabel: _t('Send Clear')
                        },{
                            xtype: 'textarea',
                            name: 'filter',
                            ref: 'filter',
                            width: 400,
                            height: 400,
                            fieldLabel: _t('Filter Source')
                        }
                    ],
                    buttons:[
                        {
                            xtype: 'button',
                            text: _t('Submit'),
                            ref: '../../submitButton',
                            formBind: true,
                            handler: function(button) {
                                var params = button.refOwner.editForm.getForm().getFieldValues();
                                var _filter = params.filter;
                                params.filter = {'content':_filter};
                                
                                config.directFn(params, function(){
                                    button.refOwner.hide();
                                    config.reloadFn();
                                });
                            }
                        },{
                            xtype: 'button',
                            ref: '../../cancelButton',
                            text: _t('Cancel'),
                            handler: function(button) {
                                button.refOwner.hide();
                            }
                        },{
                            xtype: 'button',
                            ref: '../../validateSource',
                            text: _t('Check Filter'),
                            handler: function(button) {
                                var params = {
                                    source: button.refOwner.editForm.filter.getValue()
                                };
                                config.validateFn(params, function(response){
                                    if (response.success) {
                                        Zenoss.message.success('Filter source validated successfully.');
                                    }
                                });
                                
                            }
                        }]
                    }
            });
            EditTriggerDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            this.editForm.uuid.setValue(data.uuid);
            this.editForm.enabled.setValue(data.enabled);
            this.editForm.name.setValue(data.name);
            this.editForm.delay_seconds.setValue(data.delay_seconds);
            this.editForm.repeat_seconds.setValue(data.repeat_seconds);
            this.editForm.send_clear.setValue(data.send_clear);
            this.editForm.filter.setValue(data.filter.content);
        }
    });
    Ext.reg('edittriggerdialogue', EditTriggerDialogue);
    
    
    reloadTriggersGrid = function() {
        Ext.getCmp(triggersPanelConfig.id).getStore().reload();
    };
    
    displayEditTriggerDialogue = function(data) {
        editTriggerDialogue.loadData(data);
        editTriggerDialogue.show();
    };
    
    addTriggerDialogue = new AddTriggerDialogue({
        title: _t('Add Trigger'),
        directFn: router.addTrigger,
        reloadFn: reloadTriggersGrid
    });
    
    editTriggerDialogue = new EditTriggerDialogue({
        title: _t('Edit Trigger'),
        directFn: router.updateTrigger,
        reloadFn: reloadTriggersGrid,
        validateFn: router.parseFilter
    });

    colModel = new Ext.grid.ColumnModel(colModelConfig);
    
    TriggersGridPanel = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                autoExpandColumn: 'name',
                stripeRows: true,
                cm: colModel,
                store: {
                    xtype: 'directstore',
                    directFn: router.getTriggers,
                    root: 'data',
                    autoLoad: true,
                    fields: ['uuid', 'enabled', 'name', 'delay_seconds', 'repeat_seconds', 'send_clear', 'filter']
                },
                sm: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            // enable/disabled the edit button
                            sm.grid.deleteButton.setDisabled(false);
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            sm.grid.deleteButton.setDisabled(true);
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                listeners: {
                    rowdblclick: function(grid, rowIndex, event) {
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayEditTriggerDialogue(row.data);
                        }
                    }
                },
                tbar:[
                    {
                        xtype: 'button',
                        iconCls: 'add',
                        ref: '../addButton',
                        handler: function(button) {
                            addTriggerDialogue.show();
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        ref: '../deleteButton',
                        handler: function(button) {
                            var row = button.refOwner.getSelectionModel().getSelected(),
                                uuid, params, callback;
                            if (row){
                                uuid = row.data.uuid;
                                // show a confirmation
                                Ext.Msg.show({
                                    title: _t('Delete Trigger'),
                                    msg: String.format(_t("Are you sure you wish to delete the trigger, {0}?"), row.data.name),
                                    buttons: Ext.Msg.OKCANCEL,
                                    fn: function(btn) {
                                        if (btn=="ok") {
                                            params= {
                                                uuid:uuid
                                            };
                                            callback = function(response){
                                                // item removed, reload grid.
                                                button.refOwner.deleteButton.setDisabled(true);
                                                button.refOwner.customizeButton.setDisabled(true);
                                                reloadTriggersGrid();
                                            };
                                            router.removeTrigger(params, callback);
                                            
                                        } else {
                                            Ext.Msg.hide();
                                        }
                                    }
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'customize',
                        disabled:true,
                        ref: '../customizeButton',
                        handler: function(button){
                            var row = button.refOwner.getSelectionModel().getSelected();
                            if (row) {
                                displayEditTriggerDialogue(row.data);
                            }
                        }
                    }
                ]
            });
            TriggersGridPanel.superclass.constructor.call(this, config);
        },
        setContext: function(uuid) {
            this.getStore().load();
        }
    });
    Ext.reg('TriggersGridPanel', TriggersGridPanel);
    
    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            'border':false
        },
        items: [
            masterPanelConfig,  // navigation
            detailPanelConfig   // content panel
        ]
    });

});